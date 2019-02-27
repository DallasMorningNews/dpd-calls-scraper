import csv
from datetime import datetime
from datetime import timedelta
from io import StringIO
import logging
import os

import dataset
import requests


FEED_URL = ('https://www.dallasopendata.com/resource/are8-xahz.json?$$'
            'exclude_system_fields=false')


logger = logging.getLogger()
logger.setLevel(logging.INFO)


db = dataset.connect(os.environ.get('DATABASE_URL', ''))


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

    outfile = StringIO()
    csv_out = csv.DictWriter(outfile, csv_cols, extrasaction='ignore')

    csv_out.writeheader()

    for call in calls:
        csv_out.writerow(call)

    outfile.seek(0)

    return outfile


def send_daily_report(*args):
    """Send a CSV with the last 25 hours of incident data"""
    if os.environ.get('REPORT_RECIPIENTS') is None:
        logger.info('Skipping daily report because REPORT_RECIPIENTS is empty')
        return

    logger.info('E-mailing daily report.')

    # Go back a day, plus an hour to be safe
    from_datetime = datetime.now() - timedelta(days=1, hours=1)
    csv_report = generate_csv_report(from_datetime)

    report_filename = '%s-daily-report.csv' % datetime.strftime(
        from_datetime, '%Y%m%d'
    )
    msg_text = 'CSV file with past 25 hours of DPD calls for service attached.'

    to_addresses = ', '.join([
        _.strip() for _ in os.environ['REPORT_RECIPIENTS'].split(',')
    ])

    # Send using the Mailgun API
    r = requests.post(
        'https://api.mailgun.net/v2/%s/messages' % os.environ.get(
            'MAILGUN_DOMAIN'
        ),
        auth=('api', os.environ.get('MAILGUN_API_KEY', '')),
        files=[
            ('attachment', (report_filename, csv_report.read()))
        ],
        data={
            'from': 'Active call bot <no-reply@postbox.dallasnews.com>',
            'to': to_addresses,
            'subject': 'DPD calls for %s' % datetime.strftime(
                from_datetime, '%m/%d'
            ),
            'text': msg_text
        }
    )
    r.raise_for_status()

    db['report_log'].insert(dict(
        recipients=to_addresses,
        type='daily',
        report_time=datetime.now(),
        time_sent=datetime.now()
    ))


def scrape_active_calls(*args):
    """Scrape active calls and save them into our database"""
    if 'HEALTHCHECK_URL' in os.environ:
        try:
            requests.get('%s/start' % os.environ['HEALTHCHECK_URL'], timeout=5)
        except requests.exceptions.RequestException:
            pass

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
        active_call['incident_element_id'] = '%s-%s' % (
            active_call['incident_number'],
            active_call['unit_number']
        )
        calls_table.upsert(active_call, ['incident_element_id'])

    num_added = calls_table.count() - original_count

    logger.info(
        'Scraped %s active calls (%s new).' % (len(r.json()), num_added)
    )

    if 'HEALTHCHECK_URL' in os.environ:
        requests.get(os.environ['HEALTHCHECK_URL'])


if __name__ == '__main__':
    logging.basicConfig()
    scrape_active_calls()
