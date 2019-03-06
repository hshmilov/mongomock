#!/usr/bin/env bash

if [ $# -ne 3 ] && [ $# -ne 4 ]; then
    echo "Usage: $0 access_key key_secret name_of_version [--prod]"
    exit -1
fi

export AWS_ACCESS_KEY_ID=$1
export AWS_SECRET_ACCESS_KEY=$2
installer_to_upload=$3
region=us-east-2

echo "Copying upgrader to automatic tests folder"
aws s3 cp s3://axonius-releases/${installer_to_upload}/axonius_${installer_to_upload}.py \
s3://axonius-releases/latest/axonius_latest.py \
--acl public-read \
--region ${region}

if [[ $4 == "--prod" ]]; then
    echo "Copying upgrader to production"
    aws s3 cp s3://axonius-releases/${installer_to_upload}/axonius_${installer_to_upload}.py \
    s3://axonius-releases/latest_release/axonius_upgrader.py \
    --acl public-read \
    --region ${region}
    echo "Copying OVA to production"
    aws s3 cp s3://axonius-releases/${installer_to_upload}/${installer_to_upload}/${installer_to_upload}_export.ova \
    s3://axonius-releases/latest_release/axonius_release.ova \
    --acl public-read \
    --region ${region}
    echo "Files copied to production"
fi
