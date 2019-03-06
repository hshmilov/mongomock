#!/usr/bin/env bash

set -e

if [ $# -ne 4 ]; then
    echo "Usage: $0 access_key key_secret name_of_version commit_hash"
    exit -1
fi

export AWS_ACCESS_KEY_ID=$1
export AWS_SECRET_ACCESS_KEY=$2
name_of_version=$3
commit_hash=$4

git tag ${name_of_version} ${commit_hash}
git push upstream ${name_of_version}

source upload_to_aws_latest.sh ${AWS_ACCESS_KEY_ID} ${AWS_SECRET_ACCESS_KEY} ${name_of_version} --prod

echo "Release checklist is finished successfully!"
