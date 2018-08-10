# DPD active calls scraper for AWS Lambda

This scraper runs on AWS Lambda and scrapes DPD's [active calls list](https://www.dallasopendata.com/Police/Dallas-Police-Active-Calls/9fxf-t2tr) using the [Socrata API](https://dev.socrata.com/docs/endpoints.html). One call per incident number is saved to a PostgreSQL database, allowing us to store active call information that is otherwise purged from DPD's open data portal.

It also sends a CSV once per day (at 9 a.m.) with the past 25 hour of calls.

## Requirements

- Python 3.6 - `brew install python3`
- Pipenv - `brew install pipenv`

## Local development

### Installation

1. Install dependencies:
    ```sh
    $ pipenv install --development
    ```

2. Copy the _.env.example_ to _.env_ and add AWS credentials (required for deployment) a `DATABASE_URL` (required to test storage to PostgreSQL), Mailgun credentials (to test e-mail feature) and, optionally, set `REPORT_RECIPIENTS` to a comma-separated list of everyone you'd like to receive daily reports.

### Deploying

Deployment to Lambda and management of scheduled tasks (scraping and daily report sending) are handled by `zappa`. Deploy updates with:

```sh
$ pipenv run zappa update
```

See the [complete Zappa docs](https://github.com/Miserlou/Zappa) for a full list of available commands to manage the app's configuration.

Environment variables can be updated using this function's Lambda configuration in the AWS console.

## Copyright

&copy; 2018 The Dallas Morning News
