#!/usr/bin/env bash
source bash_imports.sh
source ./testing/test_credentials/docker_login.sh

docker pull $IMAGE_NAME
create_axonius_manager
run_in_axonius_manager ./axonius.sh system build --all --prod --hard --yes-hard --rebuild-libs
run_in_axonius_manager ./axonius.sh system up --restart --all --prod
