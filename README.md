# DPD active calls scraper for AWS Lambda

tk

## Installation

1. Create a Python 2 virtual environment: `virtualenv venv`
2. Install requirements: `pip install -r requirements.txt`
3. Copy _[config.json.example](config.json.example)_ to _config.json_ and fill in the required security credentials.

## Deploying to Lambda

The easiest way to package the script for deployment to Lambda is to run the included [packaging script](package.sh) from within the app's root directory while in the virtual environment. It will:

1. Create a .zip file in the root with all of our custom code (anything with a .py extension in the project root).
2. Copy the site packages folder from our virtual environment into the .zip file, [as required by Lambda](http://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html).
3. Download a version of `psycopg2` that's [built for Lambda](https://github.com/jkehler/awslambda-psycopg2) and package it with our code in the .zip file.

The .zip that's output, which will be saved as _lambda.zip_ in the project root, can now be uploaded to the AWS console.

## Copyright

&copy; 2016 The Dallas Morning News
