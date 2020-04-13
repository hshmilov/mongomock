#!/usr/bin/env bash

set -e # from now on exit on any error

devops/super_clean.sh $@

echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
time docker pull nexus.pub.axonius.com/axonius/axonius-base-image
echo "Pulling Weave images"
time docker pull nexus.pub.axonius.com/axonius/weave:2.6.0
time docker pull nexus.pub.axonius.com/axonius/weaveexec:2.6.0
time docker pull nexus.pub.axonius.com/axonius/weavedb

# Note! prepare_setup.py should be the last thing in the script, since the return value
# of the whole script will be its return value. The CI uses this return value to know if
# we continue to the other stages.

echo "Building all images"
python3.6 -u devops/prepare_setup.py $@
if [ $? -eq 0 ]
then
  echo "Successfully built images"
else
  echo "Could not build images"
  exit 1
fi

# Now we have to use some scripts the system uses, lets active the venv
source ./prepare_python_env.sh

./download_artifacts.sh
if [ $? -eq 0 ]
then
  echo "Successfully downloaded artifacts"
else
  echo "Could not download artifacts"
  exit 1
fi

install/metadata.sh > shared_readonly_files/__build_metadata
