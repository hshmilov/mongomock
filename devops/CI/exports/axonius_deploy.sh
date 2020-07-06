#!/usr/bin/env bash
set -e
branch=$1
fork=$2
sudo_pass=$3
build_name=$4
build_mode=$5
rm -rf cortex
git clone https://b1654a5e47ffc47b5e945f0c3d34bdced6ec2ab6@github.com/$fork/cortex
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
