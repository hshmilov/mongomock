#!/usr/bin/env bash

source ./prepare_python_env.sh

if [ $(git ls-files | grep "\.py" | xargs autopep8 --max-line-length 120 --diff | wc -l) -ne 0 ]; then
    echo "Formatting failed!"
    git ls-files | grep "\.py" | xargs autopep8 --max-line-length 120 --diff
    exit 1
fi

if [ $(git ls-files | grep "\.py" | xargs autopep8 --select=E722 --diff -a | wc -l) -ne 0 ]; then
    echo "Bare 'except:' in the code, please change to 'except Exception:'"
    git ls-files | grep "\.py" | xargs autopep8 --select=E722 --diff -a
    exit 1
fi

if [ $(git ls-files | grep -E "(\.py|\.sh|\.yml|Dockerfile)" | xargs grep $(printf "\r") -r | wc -l) -ne 0 ]; then
    echo "Windows ending files failed!"
    exit 1
fi

grep -q -v "==" ./requirements.txt ./libs/axonius-base-image/requirements*
if [ $? -ne 1 ]; then
    echo "some requirements.txt file doesn't have == in all lines!"
    exit 1
fi

# We must delete old data, or else tests will fail.
# In order to delete them, we must stop the current containers first. We are going to do that anyway
# in the integration tests.
RUNNING_DOCKERS=$( docker ps -a -q )
if [ "$RUNNING_DOCKERS" != "" ]; then
    docker rm -f ${RUNNING_DOCKERS}
fi
AVAILABLE_VOLUMES=$( docker volume ls -q )
if [ "$AVAILABLE_VOLUMES" != "" ]; then
    docker volume rm ${AVAILABLE_VOLUMES}
fi

echo "Running rest mock server"
python3 ./testing/mocks/rest_server.py &> ./logs/mock_server.log &
