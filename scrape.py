import csv
from datetime import datetime, time, timedelta
import json
import logging
import os
import StringIO

import dataset
import requests


FEED_URL = ('https://www.dallasopendata.com/resource/are8-xahz.json?$$'
            'exclude_system_fields=false')
REPORT_RECIPIENTS = ('ttsiaperas@dallasnews.com', 'nrajwani@dallasnews.com',)
REPORT_TIME = time(14)  # in UTC Time


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_config():
    """Load our app config from JSON in the project root"""
    app_dir = os.path.dirname(os.path.realpath(__file__))
    config_file_path = os.path.join(app_dir, 'config.json')

    with open(config_file_path, 'r') as config_file:
        config = config_file.read()

    return json.loads(config)


config = get_config()
db = dataset.connect(config.get('database', ''))


def parse_time(time_str):
    """Parse an ISO-8601 timestamp into a Python datetime"""
    try:
        return datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%f')


def generate_csv_report(from_time):
    """Generate a CSV that has all rows since from_time (UTC), minus system
    columns."""
    calls_table_cols = db['calls'].columns

    cols_to_exclude = [':updated_at_dt', ':created_at_dt', ':id',
                       ':updated_at', ':created_at', 'date_time_dt']
    csv_cols = [c for c in calls_table_cols if c not in cols_to_exclude]

    from_time_string = datetime.strftime(from_time, '%Y-%m-%dT%H:%M:%S')
    q = ('select * from calls '
         'where date_time_dt > \'%s\' '
         'order by date_time_dt desc')
    calls = db.query(q % from_time_string)

    outfile = StringIO.StringIO()
    csv_out = csv.DictWriter(outfile, csv_cols, extrasaction='ignore')

    csv_out.writeheader()

    for call in calls:
        csv_out.writerow(call)

    outfile.seek(0)

    return outfile


def send_daily_report():
    """Send a CSV with the last 25 hours of incident data"""
    todays_report_time = datetime.combine(
        datetime.today(),
        REPORT_TIME
    )

    if datetime.now() < todays_report_time:
        logger.info('Skipping daily report. It\'s not time yet.')
        return

    report_log = db['report_log']

    if report_log.find_one(report_time=todays_report_time) is not None:
        logger.info('Skipping daily report. Already sent today.')
        return

    logger.info('E-mailing daily report.')

    # Go back a day, plus an hour to be safe
    from_datetime = datetime.now() - timedelta(days=1, hours=1)
    csv_report = generate_csv_report(from_datetime)

    report_filename = '%s-daily-report.csv' % datetime.strftime(
        from_datetime, '%Y%m%d')
    msg_text = 'CSV file with past 25 hours of DPD calls for service attached.'
    to_addresses = ', '.join(REPORT_RECIPIENTS)

    # Send using the Mailgun API
    r = requests.post(
        'https://api.mailgun.net/v2/%s/messages' % config.get('mailgunDomain'),
        auth=('api', config.get('mailgunApiKey', '')),
        files=[
            ('attachment', (report_filename, csv_report.read()))
        ],
        data={
            'from': 'Active call bot <no-reply@postbox.dallasnews.com>',
            'to': to_addresses,
            'bcc': 'achavez@dallasnews.com',
            'subject': 'DPD calls for %s' % datetime.strftime(
                from_datetime, '%m/%d'),
            'text': '%s' % msg_text,
            'html': '<html>%s</html>' % msg_text
        }
    )
    r.raise_for_status()

    report_log.insert(dict(
        recipients=to_addresses,
        type='daily',
        report_time=todays_report_time,
        time_sent=datetime.now()
    ))


def scrape_active_calls(*args):
    """Scrape active calls and save them into our database"""
    calls_table = db['calls']

    original_count = calls_table.count()

    r = requests.get(FEED_URL)
    r.raise_for_status()

    for active_call in r.json():
        parsed_dates = {
            'date_time_dt': parse_time(active_call['date_time']),
            ':created_at_dt': parse_time(active_call[':created_at']),
            ':updated_at_dt': parse_time(active_call[':updated_at'])
        }
        active_call.update(**parsed_dates)
        calls_table.upsert(active_call, ['incident_number'])

    num_added = calls_table.count() - original_count

    logger.info(
        'Scraped %s active calls (%s new).' % (len(r.json()), num_added)
    )

    send_daily_report()


if __name__ == '__main__':
    logging.basicConfig()
    scrape_active_calls()
