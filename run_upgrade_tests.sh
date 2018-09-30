#!/usr/bin/env bash

set -e
version="head"
installer_name=axonius_${version}.py
install_dir="install_dir"

mkdir -p logs
mkdir -p ${install_dir}

echo "#### Creating venv"
./create_venv.sh &> logs/create_venv.log
echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
echo "#### Creating venv done"

echo "#### Creating installer"
./pyrun.sh ./deployment/make.py --version ${version}  --rebuild --pull --exclude traiana_lab_machines json_file qcore stresstest_scanner stresstest infinite_sleep &> logs/create_installer.log
mv ${installer_name} ${install_dir}/
echo "#### Installer created"

echo "#### Cleaning env"
set +e; ./clean_dockers.sh images &>/dev/null; set -e # can fail and its ok; also images
echo "#### Cleaning done"

# install latest stable version from scratch (can fetch from aws or exports).
# assume we put our latest stable at the following location.
echo "#### Installing latest stable version"
cd ${install_dir}
wget -q https://s3.us-east-2.amazonaws.com/axonius-releases/latest/axonius_latest.py
chmod +x ./axonius_latest.py
sudo ./axonius_latest.py --first-time &> ../logs/install_latest_stable.log
cd ..
echo "#### Latest stable version installed"

echo "#### Populate latest stable with data"
set +e; ./pyrun.sh devops/scripts/automate_dev/credentials_inputer.py; set -e;
./pyrun.sh devops/scripts/discover_now.py --wait
echo "#### Populating with data finished"

echo "#### Running before upgrade setups"
cd testing
../pyrun.sh run_upgrade_tests.py --teardown-keep-db upgrade/before_upgrade
cd ..
echo "#### Before upgrade setups done"

echo "#### Upgrading to ${version}"
cd ${install_dir}
chmod +x ${installer_name}
sudo ./${installer_name} &> ../logs/upgrade_to_${version}.log
cd ..
echo "#### Installed ${version}"

echo "#### Running after upgrade tests"
./pyrun.sh devops/scripts/discover_now.py --wait
cd testing
../pyrun.sh run_upgrade_tests.py --teardown-keep-db upgrade/after_upgrade
cd ..
echo "#### After upgrade tests done"
