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
axonius system up --all --prod
)

echo "Removing anything irrelevant.."
(
# tests
rm -rf ./testing/tests/ ./testing/parallel_tests/ ./testing/reporting ./testing/.cache */*/tests
# misc
rm -rf .git* .idea* .cache* *.bat *.sh ./devops
history -c
history -w
)

echo "Done."