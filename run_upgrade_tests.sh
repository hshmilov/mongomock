#!/usr/bin/env bash

echo "download weave version"
weave_path="/usr/local/bin/weave"
source testing/test_credentials/docker_login.sh
sudo cp devops/scripts/host_installation/uploads/weave-2.7
.0 ${weave_path}
sudo chmod a+x ${weave_path}
sudo weave status
docker pull nexus.pub.axonius.com/axonius/axonius-manager
./run_axonius_manager.sh
docker exec axonius-manager testing/test_credentials/docker_login.sh
tar czf /tmp/testing.tgz testing/

function finish {
  exit_code=$?
  set +e
  echo "#### In finish function"
  # In case where it won't work, it does not matter since regular clean_dockers.sh was called.
  pwd
  cd ..
  ./clean_dockers.sh
  echo "#### After finish function"
  exit $exit_code
}
trap finish EXIT

set -e
version="head"
installer_name=axonius_${version}.py
install_dir="install_dir"
upgrade_version_name=$1

mkdir -p logs
mkdir -p ${install_dir}


#echo "Setting Up Docker Service"
#sudo systemctl restart docker

#echo "Installing golang"
#sudo rm -f /etc/apt/sources.list.d/jonathonf-ubuntu-python-3_6-xenial.list /etc/apt/sources.list.d/jonathonf-ubuntu-python-3_6-xenial.list.save
#sudo ./go_install.sh

#echo "#### Creating venv"
#./create_venv.sh &> logs/create_venv.log
#cd bandicoot && go mod vendor && cd ..
echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
#echo "#### Creating venv done"

echo "#### Creating installer - Inside host container"
docker exec axonius-manager pip3 -V
docker exec axonius-manager /bin/bash -c "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY python3 ./deployment/make.py --version ${version} --rebuild --pull &> logs/create_installer.log"
sudo chown ubuntu:ubuntu logs/create_installer.log
echo "#### make.py Finished"
mv ${installer_name} ${install_dir}/
echo "#### Installer created"

echo "#### Cleaning env"
# Run the clean dockers from inside containers so it wont delete axonius-manager
set +e; docker exec axonius-manager ./clean_dockers.sh images &>/dev/null; set -e # can fail and its ok; also images
weave reset
echo "#### Cleaning done"

# install latest stable version from scratch (can fetch from aws or exports).
# assume we put our latest stable at the following location.
echo "#### Installing latest stable version"
cd ${install_dir}
docker exec -w /home/ubuntu/cortex/$install_dir axonius-manager python3 ../devops/scripts/automate_dev/download_version.py -o "$(pwd)"/axonius_latest.py -v "${upgrade_version_name}"
sudo chmod +x ./axonius_latest.py
if [[ "$(head -n 1 axonius_latest.py)" == "#!/bin/sh" ]];then
  # The new makeself installer
  sudo ./axonius_latest.py -- --first-time &> ../logs/install_latest_stable.log
else
  # The old python ZipApp installer
  sudo ./axonius_latest.py --first-time &> ../logs/install_latest_stable.log
fi

cd cortex
if [ -f run_axonius_manager.sh ]; then
  # Check if its new version with host container
  ./run_axonius_manager.sh
  docker exec axonius-manager ./axonius.sh system up --all --restart --prod &> ../../logs/start_latest_stable.log
else
  ./axonius.sh system up --all --restart --prod &> ../../logs/start_latest_stable.log
fi
cd ..

cd ..
echo "#### Latest stable version installed"

echo "#### Populate latest stable with data"
if [ -f run_axonius_manager.sh ]; then
  set +e; docker exec axonius-manager python3 devops/scripts/automate_dev/credentials_inputer.py; set -e;
  docker exec axonius-manager python3 devops/scripts/discover_now.py --wait
else
  set +e; python3 devops/scripts/automate_dev/credentials_inputer.py; set -e;
  python3 devops/scripts/discover_now.py --wait
fi
echo "#### Populating with data finished"

echo "#### Running before upgrade setups"
set +e; timeout 3600 docker exec -w /home/ubuntu/cortex/testing axonius-manager python3 run_upgrade_tests.py --teardown-keep-db upgrade/before_upgrade -p no:testing/tests/conftest.py; set -e;

echo "#### Before upgrade setups done"


# Block pypi
if [ -f run_axonius_manager.sh ]; then
  docker exec axonius-manager python3 testing/ui_tests/tests/hosts_file_modifier.py 1.2.3.4 pypi.python.org &> logs/upgrade_to_version.log
  docker exec axonius-manager python3 testing/ui_tests/tests/hosts_file_modifier.py 1.2.3.4 files.pythonhosted.org &> logs/upgrade_to_version.log
else
  python3 testing/ui_tests/tests/hosts_file_modifier.py 1.2.3.4 pypi.python.org &> logs/upgrade_to_version.log
  python3 testing/ui_tests/tests/hosts_file_modifier.py 1.2.3.4 files.pythonhosted.org &> logs/upgrade_to_version.log
fi

echo "#### Upgrading to ${version}"
pip -V
cd ${install_dir}
sudo chmod +x ${installer_name}
sudo /bin/sh -c "./${installer_name} -- --master-only" 2>&1 > ../logs/upgrade_to_version.log &
sleep 1000
while [ $(tail -n 5 ../logs/upgrade_to_version.log | grep -c "Upgrader completed") -eq 0 ]; do
  sleep 60
done
if [ $(grep -c "Upgrader completed - failure" ../logs/upgrade_to_version.log) -ne 0 ];then
    echo "Upgrade failed!!!"
    exit 1
fi
cd ..
echo "#### Installed ${version}"

echo "#### Running after upgrade tests"
set +e; timeout 800 docker exec axonius-manager python3 devops/scripts/discover_now.py --wait; set -e
pwd
set +e; sudo cp /home/ubuntu/BuildAgent/work/cortex/testing/account_data.tmp /home/ubuntu/BuildAgent/work/cortex/install_dir/cortex/testing; set -e
sudo /bin/sh -c "rm -rf testing/; cp /tmp/testing.tgz .; tar xzf testing.tgz; sudo chown -R ubuntu:ubuntu testing;"
set +e; sudo cp /home/ubuntu/BuildAgent/work/cortex/install_dir/cortex/testing/account_data.tmp /home/ubuntu/BuildAgent/work/cortex/testing/; set -e
ls -la ./testing/test_credentials/docker_login.sh

sudo ./run_axonius_manager.sh
./testing/test_credentials/docker_login.sh
docker exec axonius-manager /bin/sh ./testing/test_credentials/docker_login.sh
docker pull nexus.pub.axonius.com/elgalu/selenium:3.141.59-p32
docker exec -d axonius-manager python3 ./devops/create_pth.py
sleep 5
set +e; timeout 3600 docker exec -w /home/ubuntu/cortex/testing axonius-manager python3 run_upgrade_tests.py --teardown-keep-db upgrade/after_upgrade -p no:testing/tests/conftest.py; set -e;

echo "#### After upgrade tests done"

echo "#### Testing node_maker missing on host after upgrade"
if [[ $(grep -q "node_maker" /etc/passwd) == 0 ]]; then
    echo "node_maker exists after upgrade!!!"
    exit 1
fi
echo "#### node_maker does NOT exist after upgrade!!!"

set +e; timeout 60 sudo ./clean_dockers.sh; set -e # can fail and its ok;
echo "#### After upgrade stop all"
