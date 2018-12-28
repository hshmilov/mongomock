#!/usr/bin/env bash
set -e # from now on exit on any error

source prepare_python_env.sh
eval $(/usr/local/bin/weave env)
cd "$(dirname "$0")"
cd devops
python3 -u axonius_system.py $@