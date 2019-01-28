#!/usr/bin/env bash
set -e # from now on exit on any error

source prepare_python_env.sh
cd "$(dirname "$0")"
cd devops/SE
python3 se.py $@