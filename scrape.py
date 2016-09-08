import os
import json

import requests
import dataset


FEED_URL = ('https://www.dallasopendata.com/resource/are8-xahz.json?$$'
            'exclude_system_fields=false')


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

    r = requests.get(FEED_URL)
    r.raise_for_status()

    for active_call in r.json():
        calls_table.upsert(active_call, ['incident_number'])


if __name__ == '__main__':
    scrapeActiveCalls()
