#!/usr/bin/env bash
set -e
branch=$1
fork=$2
sudo_pass=$3
build_name=$4
build_mode=$5
rm -rf cortex
git clone https://0e28371fe6803ffc7cba318c130a465e9f28d26f@github.com/$fork/cortex
cd cortex
git checkout $branch
# add go packages
cd bandicoot
go mod vendor
cd ..
./create_venv.sh
source venv/bin/activate
chmod u+x ./testing/test_credentials/docker_login.sh
./testing/test_credentials/docker_login.sh
python3 ./deployment/make.py --version "$build_name" --mode "$build_mode" --rebuild --pull
