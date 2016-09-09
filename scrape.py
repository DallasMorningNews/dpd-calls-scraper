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


def scrapeActiveCalls(*args):
    """Scrape active calls and save them into our database"""
    config = get_config()

    db = dataset.connect(config.get('database', ''))
    calls_table = db['calls']

    original_count = calls_table.count()

    r = requests.get(FEED_URL)
    r.raise_for_status()

    for active_call in r.json():
        calls_table.upsert(active_call, ['incident_number'])

    num_added = calls_table.count() - original_count

    logger.info(
        'Scraped %s active calls (%s new).' % (len(r.json()), num_added)
    )


if __name__ == '__main__':
    logging.basicConfig()
    scrapeActiveCalls()
