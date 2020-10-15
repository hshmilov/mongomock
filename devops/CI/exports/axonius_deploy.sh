#!/usr/bin/env bash
set -e
github_token=$1
branch=$2
fork=$3
sudo_pass=$4
build_name=$5
build_mode=$6
rm -rf cortex
git clone https://$github_token@github.com/$fork/cortex
cd cortex
git checkout $branch
chmod u+x ./testing/test_credentials/docker_login.sh
./testing/test_credentials/docker_login.sh
sudo python3 -m pip install -r requirements.txt --ignore-installed
sudo python3 ./devops/create_pth.py
python3 ./deployment/make.py --version "$build_name" --mode "$build_mode" --rebuild --pull
