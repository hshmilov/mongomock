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

echo "Done."