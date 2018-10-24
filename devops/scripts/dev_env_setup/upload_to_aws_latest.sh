#!/usr/bin/env bash

if [ $# -ne 3 ]; then
    echo "Usage: $0 access_key key_secret file_to_upload"
    exit -1
fi

AWS_ACCESS_KEY_ID=$1
AWS_SECRET_ACCESS_KEY=$2
installer_to_upload=$3
region=us-east-2

aws s3 cp $installer_to_upload \
s3://axonius-releases/latest/axonius_latest.py \
--acl public-read \
--region $region
