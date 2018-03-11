#!/usr/bin/env bash

# go to projects main dir
cd ..

optional_parameters=$1

echo "Appending Metadata"
(
install/metadata.sh >> __build_metadata
)

echo "Building all..."
(
./prepare_ci_env.sh
docker logout
)

echo "Running all..."
(
eval ./axonius.sh system up --all ${optional_parameters}
)

echo "Setting all credentials."
(
source ./prepare_python_env.sh
python3 ./devops/scripts/credentials_inputer.py
./axonius.sh service aggregator up --restart
)

echo "Done."