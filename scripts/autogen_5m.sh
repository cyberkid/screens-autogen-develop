#!/bin/bash

set -x # trace commands
set -e # exit as soon as a command fails

echo "Executing autogen-screens script for 5m update screens."
# All screens updated via this script should be the ones that are expected to update every 5min

echo "checking disk space"
df -h .

echo "Installing system dependancies"
sudo apt-get install python-dev libxslt1.1 libxml2 libev-dev g++ libxml2-dev libxslt-dev || true
#sudo pip install datadog

echo "#) Create virtualenv - sets up the env in which the screen generator runs"
export VENV_PATH=venv
make virtualenv

echo "#) Activate virtualenv"
source $VENV_PATH/bin/activate

rm -rf out # remove directory and all its contents. This directory might exist from previous run.
mkdir out # output directory

[ -z "$S3_CFG_PATH" ] && S3_CFG_PATH=$HOME/.s3cfg
export S3_CFG_PATH

export S3CMD_PATH=`which s3cmd`

echo "#) Generate screens for the specified env and group and deploy to env"
python ./src/screen_generator.py -e $DEPLOY_ENV -g $SCREEN_GROUP -o ./out/


echo "#) DONE"
