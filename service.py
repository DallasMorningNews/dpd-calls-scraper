import csv
from datetime import datetime
from datetime import timedelta
from io import StringIO
import logging
import os

import dataset
import requests

import sentry_sdk
sentry_sdk.init("https://000d6ee8e0734404aeaeab2cd07afa27@o101507.ingest.sentry.io/5262187")



FEED_URL = ('https://www.dallasopendata.com/resource/are8-xahz.json?$$'
            'exclude_system_fields=false')

EMAIL_HEALTHCHECK_URL = (
    'https://hc-ping.com/dd07eb0c-c57e-4575-9fab-8068e1db6a72'
)

SCRAPER_HEALTHCHECK_URL = (
    'https://hc-ping.com/2ba25034-04bc-4f1a-8b57-49b1120c79c2'
)


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
    try:
        requests.get('%s/start' % EMAIL_HEALTHCHECK_URL, timeout=5)
    except requests.exceptions.RequestException:
        pass

    if os.environ.get('REPORT_RECIPIENTS') is None:
        logger.info('Skipping daily report because REPORT_RECIPIENTS is empty')
        requests.get(EMAIL_HEALTHCHECK_URL)
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
    requests.get(EMAIL_HEALTHCHECK_URL)


def convert24(str1):

    date_time_string = datetime.strptime(str1, '%I:%M%p')
    return date_time_string.strftime('%H:%M:%S')


def parse_time_string(time_str):
    # date_split = time_str.split(' ')
    # months = {
    #     'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
    #     'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
    #     'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12',
    #     }
    # new_date_split = []
    # for v in date_split:
    #     if v:
    #         new_date_split.append(v)

    # month = months[new_date_split[0]]
    # day = new_date_split[1]
    # year = new_date_split[2]
    # time_split = new_date_split[3].split(":")
    # hour = time_split[0]
    # minute = time_split[1][:2]
    # ampm = time_split[1][2:]

    # datestr = '{}-{}-{}'.format(year, month, day)
    # timestr = '{}:{}:00 {}'.format(hour, minute, ampm)
    # timefinal = convert24(timestr)

    # datetimestr = '{}T{}'.format(datestr, timefinal)

    timefinal = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S')

    return timefinal


def scrape_active_calls(*args):
    """Scrape active calls and save them into our database"""
    try:
        requests.get('%s/start' % SCRAPER_HEALTHCHECK_URL, timeout=5)
    except requests.exceptions.RequestException:
        pass

    calls_table = db['calls']

    original_count = calls_table.count()

    r = requests.get(FEED_URL)
    r.raise_for_status()

    for active_call in r.json():
        calldate = active_call['date'].split('T')[0]
        # convert the time of the incident to 24 hour format
        # calltime = convert24(active_call['time'])
        # add the date and time back as a complete date_time string to the call
        active_call['date_time'] = calldate + 'T' + active_call['time']
      
        parsed_dates = {
            'date_time_dt': parse_time_string(active_call['date_time']),
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

    requests.get(SCRAPER_HEALTHCHECK_URL)


if __name__ == '__main__':
    logging.basicConfig()
    scrape_active_calls()
    # send_daily_report()