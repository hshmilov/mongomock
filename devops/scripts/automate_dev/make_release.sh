#!/usr/bin/env bash

if [ $# -ne 4 ]; then
    echo "Usage: $0 access_key key_secret name_of_export name_of_version"
    exit -1
fi

export AWS_ACCESS_KEY_ID=$1
export AWS_SECRET_ACCESS_KEY=$2
name_of_export=$3
name_of_version=$4
region=us-east-2

echo "Copying upgrader..."
aws s3 cp s3://axonius-releases/${name_of_export}/axonius_${name_of_export}.py \
s3://axonius-releases/${name_of_version}/axonius_${name_of_version}.py \
--acl public-read \
--region ${region}

echo "Copying OVA..."
aws s3 cp s3://axonius-releases/${name_of_export}/${name_of_export}/${name_of_export}_export.ova \
    s3://axonius-releases/${name_of_version}/${name_of_version}/${name_of_version}_export.ova \
    --acl public-read \
    --region ${region}

echo "Files copied"
