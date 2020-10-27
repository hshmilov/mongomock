#!/usr/bin/env bash

# go to projects main dir
cd ..

optional_parameters=$1

echo "Appending Metadata"
(
install/metadata.sh > shared_readonly_files/__build_metadata
)

echo "Building all..."
(
./prepare_ci_env.sh
docker logout
)

if [[ $* == *--run-system* ]]; then
    echo "Running all..."
    (
    if [[ ${optional_parameters} != *"exclude"* ]]; then
        eval ./axonius.sh system up --services static_analysis device_control --adapters ${optional_parameters} --restart
    else
        eval ./axonius.sh system up --all ${optional_parameters} --restart
    fi
    )
fi

if [[ $* == *--set-credentials* ]]; then
    echo "Setting all credentials."
    (
    docker exec axonius-manager python3 ./devops/scripts/automate_dev/credentials_inputer.py
    )
fi

if [[ $* == *--set-debug-passwords* ]]; then
    echo "Setting debug passwords for Axonius users."
    (
    docker exec axonius-manager python3 ./devops/scripts/automate_dev/set_default_axonius_users.py
    )
fi

if [[ $* == *--clean* ]]; then
    echo "Removing anything irrelevant.."
    (
    # find all directories in testing, filter 'services' and 'test_helpers', and remove them.
    find testing/* -type d | grep -v "services" | grep -v "test_helpers" | xargs rm -rf
    # find recursively all directories named "tests" and remove them.
    find . -name "tests" -type d | xargs rm -rf
    # misc
    rm -rf .git* .idea* .cache* *.bat
    history -c
    history -w
    )
fi

echo "Done."