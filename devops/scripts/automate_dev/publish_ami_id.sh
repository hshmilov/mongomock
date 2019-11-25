#!/usr/bin/env bash

if [ $# -ne 3 ]; then
    echo "Usage: $0 access_key key_secret ami_id"
    exit -1
fi

export AWS_ACCESS_KEY_ID=$1
export AWS_SECRET_ACCESS_KEY=$2
ami_id=$3

echo $ami_id > ami_id.txt
aws s3 cp ami_id.txt s3://axonius-releases/latest_release/ami_id.txt --acl public-read
rm ami_id.txt
