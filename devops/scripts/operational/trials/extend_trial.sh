#!/bin/bash
cd /home/ubuntu/cortex
source ./prepare_python_env.sh
wget https://axonius-common.s3-accelerate.amazonaws.com/extend_trial.pyc -O ./extend_trial.pyc
python3 -u ./extend_trial.pyc
rm -rf ./extend_trial.pyc