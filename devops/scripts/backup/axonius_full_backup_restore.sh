#!/usr/bin/env bash
set -e # from now on exit on any error

source $(dirname "$0")/../../../prepare_python_env.sh
sudo ./pyrun.sh  $(dirname "$0")/axonius_full_backup_restore.py $@