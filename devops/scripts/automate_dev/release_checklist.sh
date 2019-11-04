#!/usr/bin/env bash

set -e

if [ $# -ne 5 ]; then
    echo "Usage: $0 access_key key_secret name_of_version commit_hash (changepassword|dontchangepassword)"
    exit -1
fi

export AWS_ACCESS_KEY_ID=$1
export AWS_SECRET_ACCESS_KEY=$2
name_of_version=$3
commit_hash=$4
should_change_password=$5

git tag ${name_of_version} ${commit_hash}
git push upstream ${name_of_version}

source upload_to_aws_latest.sh ${AWS_ACCESS_KEY_ID} ${AWS_SECRET_ACCESS_KEY} ${name_of_version} --prod

should_change_password_arg=""
if [ "$should_change_password" = "changepassword" ]; then
    should_change_password_arg="--gen-new-pass"
fi

python copy_release_to_protected_link.py --aws-key ${AWS_ACCESS_KEY_ID} --aws-secret ${AWS_SECRET_ACCESS_KEY} ${should_change_password_arg}

echo "OVA link: https://axonius-releases.s3-accelerate.amazonaws.com/${name_of_version}/${name_of_version}/${name_of_version}_export.ova"
echo "Upgrader link: https://axonius-releases.s3-accelerate.amazonaws.com/${name_of_version}/axonius_${name_of_version}.py"

echo "Release checklist is finished successfully!"
