#!/bin/bash
cd /home/ubuntu/cortex
source ./prepare_python_env.sh
wget https://axonius-common.s3-accelerate.amazonaws.com/remove_trial.pyc -O ./remove_trial.pyc
python3 -u ./remove_trial.pyc
rm -rf ./remove_trial.pyc