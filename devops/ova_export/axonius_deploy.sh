#!/usr/bin/env bash
set -e
branch=$1
fork=$2
sudo_pass=$3
build_name=$4
mkdir axonius
cd axonius
git init
git pull https://0e28371fe6803ffc7cba318c130a465e9f28d26f@github.com/$fork/cortex $branch
./create_venv.sh
source venv/bin/activate
chmod u+x ./testing/test_credentials/docker_login.sh
./testing/test_credentials/docker_login.sh
python3 ./deployment/make.py --version $build_name  --rebuild --pull --exclude traiana_lab_machines json_file qcore stresstest_scanner stresstest splunk_symantec infinite_sleep
set +e
docker kill $(docker ps -aq)
docker rm $(docker ps -aq)
docker rmi $(docker images -q)
docker volume rm $(docker volume ls -q)
set -e
docker logout
mv ./axonius_$build_name.py ../
cd ../
rm -rf axonius
deactivate
echo $sudo_pass | sudo -S python3 ./axonius_$build_name.py --first-time
echo $sudo_pass | sudo -S chown -R ubuntu:ubuntu ./cortex
cd cortex
./axonius.sh system up --restart --all --prod --exclude diagnostics