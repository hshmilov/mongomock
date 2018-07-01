#!/usr/bin/env bash

# go to projects main dir
cd ..

optional_parameters=$1

echo "Appending Metadata"
(
install/metadata.sh >> axonius-libs/__build_metadata
)

echo "Building all..."
(
./prepare_ci_env.sh
docker logout
)

if [[ $* == *--run-system* ]]; then
    echo "Running all..."
    (
    if [[ optional_parameters != *"exclude"* ]]; then
        eval ./axonius.sh system up --services general_info careful_execution_correlator execution --adapters ${optional_parameters}
    else
        eval ./axonius.sh system up --exclude qcore traiana_lab_machines stresstest stresstest_scanner json_file, infinite_sleep --all ${optional_parameters}
    fi
    )
fi

if [[ $* == *--set-credentials* ]]; then
    echo "Setting all credentials."
    (
    source ./prepare_python_env.sh
    python3 ./devops/scripts/automate_dev/credentials_inputer.py
    ./axonius.sh service aggregator up --restart
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