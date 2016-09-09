#!/usr/bin/env bash

CURRENT_DIR=$PWD
OUTFILE="$PWD/lambda.zip"
SITE_PACKAGES="$VIRTUAL_ENV/lib/python2.7/site-packages"
SITE_PACKAGES_64="$VIRTUAL_ENV/lib64/python2.7/site-packages"
PSYCOPG2_DIR="$PWD/lambda-psycopg2"

[ -f "$OUTFILE" ] && echo "* Removing existing lambda.zip" && rm $OUTFILE

echo "* Packaging config file"
zip -9 $OUTFILE config.json > /dev/null

echo "* Packaging site-packges from virtual environment"
[ -d "$SITE_PACKAGES" ] && cd $SITE_PACKAGES && zip -r9 $OUTFILE * > /dev/null
[ -d "$SITE_PACKAGES_64" ] && cd $SITE_PACKAGES_64 && zip -r9 $OUTFILE * > /dev/null

if [ ! -d "$PSYCOPG2_DIR" ]; then
  echo "* Downloading psycopg2 for AWS from Github"
  mkdir -p $PSYCOPG2_DIR
  curl -sL https://github.com/jkehler/awslambda-psycopg2/archive/master.zip -o $PSYCOPG2_DIR/master.zip > /dev/null
  unzip $PSYCOPG2_DIR/master.zip -d $PSYCOPG2_DIR/ > /dev/null
fi

echo "* Packaging pyscopg2 for AWS"
cd $PSYCOPG2_DIR/awslambda-psycopg2-master/ && zip -r9 $OUTFILE psycopg2 > /dev/null

echo "* Packaging app Python files"
cd $CURRENT_DIR && zip -9 $OUTFILE *.py > /dev/null
