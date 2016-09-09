from datetime import datetime
import json
import logging
import os

import dataset
import requests


FEED_URL = ('https://www.dallasopendata.com/resource/are8-xahz.json?$$'
            'exclude_system_fields=false')


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_config():
    """Load our app config from JSON in the project root"""
    app_dir = os.path.dirname(os.path.realpath(__file__))
    config_file_path = os.path.join(app_dir, 'config.json')

    with open(config_file_path, 'r') as config_file:
        config = config_file.read()

    return json.loads(config)


def parse_time(time_str):
    """Parse an ISO-8601 timestamp into a Python datetime"""
    try:
        return datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%f')


def scrapeActiveCalls(*args):
    """Scrape active calls and save them into our database"""
    config = get_config()

    db = dataset.connect(config.get('database', ''))
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


if __name__ == '__main__':
    logging.basicConfig()
    scrapeActiveCalls()
