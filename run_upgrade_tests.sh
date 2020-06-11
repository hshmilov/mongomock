#!/usr/bin/env bash

function finish {
  set +e
  echo "#### In finish function"
  # In case where it won't work, it does not matter since regular clean_dockers.sh was called.
  pwd
  cd ..
  ./clean_dockers.sh
  echo "#### After finish function"
}
trap finish EXIT

echo "download weave version"
weave_path="/usr/local/bin/weave"
cp devops/scripts/host_installation/weave-2.6.0 ${weave_path}
sudo chmod a+x ${weave_path}

set -e
version="head"
installer_name=axonius_${version}.py
install_dir="install_dir"
upgrade_version_name=$1

mkdir -p logs
mkdir -p ${install_dir}

echo "Setting Up Docker Service"
sudo systemctl restart docker

echo "Installing golang"
sudo rm -f /etc/apt/sources.list.d/jonathonf-ubuntu-python-3_6-xenial.list /etc/apt/sources.list.d/jonathonf-ubuntu-python-3_6-xenial.list.save
sudo ./go_install.sh

echo "#### Creating venv"
./create_venv.sh &> logs/create_venv.log
cd bandicoot && go mod vendor && cd ..
echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
echo "#### Creating venv done"

echo "#### Creating installer"
pip -V
./pyrun.sh ./deployment/make.py --version ${version} --rebuild --pull &> logs/create_installer.log
mv ${installer_name} ${install_dir}/
echo "#### Installer created"

echo "#### Cleaning env"
set +e; ./clean_dockers.sh images &>/dev/null; set -e # can fail and its ok; also images
weave reset
echo "#### Cleaning done"

# install latest stable version from scratch (can fetch from aws or exports).
# assume we put our latest stable at the following location.
echo "#### Installing latest stable version"
cd ${install_dir}
../pyrun.sh ../devops/scripts/automate_dev/download_version.py -o "$(pwd)"/axonius_latest.py -v "${upgrade_version_name}"
chmod +x ./axonius_latest.py
sudo ./axonius_latest.py --first-time &> ../logs/install_latest_stable.log

cd cortex
sudo ./axonius.sh system up --all --restart --prod &> ../../logs/start_latest_stable.log
cd ..

cd ..
echo "#### Latest stable version installed"

echo "#### Populate latest stable with data"
set +e; ./pyrun.sh devops/scripts/automate_dev/credentials_inputer.py; set -e;
./pyrun.sh devops/scripts/discover_now.py --wait
echo "#### Populating with data finished"

echo "#### Running before upgrade setups"
cd testing
timeout 3600 ../pyrun.sh run_upgrade_tests.py --teardown-keep-db upgrade/before_upgrade
cd ..
echo "#### Before upgrade setups done"


# Block pypi
sudo python3 testing/ui_tests/tests/hosts_file_modifier.py 1.2.3.4 pypi.python.org &> logs/upgrade_to_version.log
sudo python3 testing/ui_tests/tests/hosts_file_modifier.py 1.2.3.4 files.pythonhosted.org &> logs/upgrade_to_version.log

echo "#### Upgrading to ${version}"
pip -V
cd ${install_dir}
chmod +x ${installer_name}
sudo ./${installer_name} --master-only &> ../logs/upgrade_to_version.log
cd ..
echo "#### Installed ${version}"

echo "#### Running after upgrade tests"
./pyrun.sh devops/scripts/discover_now.py --wait
cd testing
timeout 3600 ../pyrun.sh run_upgrade_tests.py --teardown-keep-db upgrade/after_upgrade
cd ..
echo "#### After upgrade tests done"

echo "#### Testing node_maker missing on host after upgrade"
if [[ $(grep -q "node_maker" /etc/passwd) == 0 ]]; then
    echo "node_maker exists after upgrade!!!"
    exit 1
fi
echo "#### node_maker does NOT exist after upgrade!!!"


set +e; ./clean_dockers.sh; set -e # can fail and its ok;
echo "#### After upgrade stop all"
