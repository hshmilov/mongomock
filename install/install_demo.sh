#!/usr/bin/env bash

# go to projects main dir
cd ..

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
./axonius.sh system up --all --prod
)

echo "Setting all credentials."
(
source ./prepare_python_env.sh
python ./devops/scripts/credentials_inputer.py
./axonius.sh plugin up aggregator --restart
)

echo "Done."