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
# System
docker-compose -f infrastructures/database/docker-compose.yml -f infrastructures/database/docker-compose.prod.yml up -d
docker-compose -f plugins/core/docker-compose.yml -f plugins/core/docker-compose.prod.yml up -d
docker-compose -f plugins/aggregator-plugin/docker-compose.yml -f plugins/aggregator-plugin/docker-compose.prod.yml up -d
docker-compose -f plugins/gui/docker-compose.yml -f plugins/gui/docker-compose.prod.yml up -d

# Plugins
docker-compose -f plugins/watch-service/docker-compose.yml -f plugins/watch-service/docker-compose.prod.yml up -d
docker-compose -f plugins/static-correlator-plugin/docker-compose.yml -f plugins/static-correlator-plugin/docker-compose.prod.yml up -d
docker-compose -f plugins/execution-plugin/docker-compose.yml -f plugins/execution-plugin/docker-compose.prod.yml up -d
docker-compose -f plugins/dns-conflicts-plugin/docker-compose.yml -f plugins/dns-conflicts-plugin/docker-compose.prod.yml up -d
docker-compose -f plugins/careful-execution-correlator-plugin/docker-compose.yml -f plugins/careful-execution-correlator-plugin/docker-compose.prod.yml up -d

# Adapters
docker-compose -f adapters/ad-adapter/docker-compose.yml -f adapters/ad-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/aws-adapter/docker-compose.yml -f adapters/aws-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/epo-adapter/docker-compose.yml -f adapters/epo-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/esx-adapter/docker-compose.yml -f adapters/esx-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/jamf-adapter/docker-compose.yml -f adapters/jamf-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/nessus-adapter/docker-compose.yml -f adapters/nessus-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/nexpose-adapter/docker-compose.yml -f adapters/nexpose-adapter/docker-compose.prod.yml up -d
#docker-compose -f adapters/puppet-adapter/docker-compose.yml -f adapters/puppet-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/qualys-adapter/docker-compose.yml -f adapters/qualys-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/splunk-symantec-adapter/docker-compose.yml -f adapters/splunk-symantec-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/splunk-nexpose-adapter/docker-compose.yml -f adapters/splunk-nexpose-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/symantec-adapter/docker-compose.yml -f adapters/symantec-adapter/docker-compose.prod.yml up -d
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