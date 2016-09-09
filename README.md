# DPD active calls scraper for AWS Lambda

This scraper runs on AWS Lambda and scrapes DPD's [active calls list](https://www.dallasopendata.com/Police/Dallas-Police-Active-Calls/9fxf-t2tr) using the [Socrata API](https://dev.socrata.com/docs/endpoints.html). One call per incident number is saved to a PostgreSQL database, allowing us to store active call information that is otherwise purged from DPD's open data portal.

It also sends a CSV once per day (at 9 a.m.) with the past 25 hour of calls.

## Local development

1. Create a Python 2.7 virtual environment: `virtualenv venv`
2. Install requirements: `pip install -r requirements.txt`
3. Copy _[config.example.json](config.json.example)_ to _config.json_ and fill in the required security credentials.

## Deploying to Lambda

The easiest way to package the script for deployment to Lambda is to run the included [packaging script](package.sh) from within the app's root directory while in the virtual environment. It will:

1. Create a .zip file in the root with all of our custom code (anything with a .py extension in the project root).
2. Copy the site packages folder from our virtual environment into the .zip file, [as required by Lambda](http://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html).
3. Download a version of `psycopg2` that's [built for Amazon Linux](https://github.com/jkehler/awslambda-psycopg2) and package it with our code in the .zip file.

The .zip that's output, which will be saved as _lambda.zip_ in the project root, can now be uploaded to the AWS console.

## Copyright

&copy; 2016 The Dallas Morning News
