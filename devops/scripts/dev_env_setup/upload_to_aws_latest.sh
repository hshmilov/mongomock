#!/usr/bin/env bash

if [ $# -ne 3 ]; then
    echo "Usage: $0 access_key key_secret name_of_version"
    exit -1
fi

export AWS_ACCESS_KEY_ID=$1
export AWS_SECRET_ACCESS_KEY=$2
installer_to_upload=$3
region=us-east-2

aws s3 cp s3://axonius-releases/${installer_to_upload}/axonius_${installer_to_upload}.py \
s3://axonius-releases/latest/axonius_latest.py \
--acl public-read \
--region ${region}
