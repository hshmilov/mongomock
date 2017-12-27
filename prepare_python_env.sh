source venv/bin/activate

export CORTEX_ROOT=`cd "$(dirname "$0")" && pwd`
export PYTHONPATH="$PYTHONPATH:$CORTEX_ROOT:$CORTEX_ROOT/plugins/core/src:\
$CORTEX_ROOT/plugins/axonius-libs/src/libs/axonius-py:\
$CORTEX_ROOT/plugins/aggregator-plugin/src:\
$CORTEX_ROOT/plugins/execution-correlator-plugin/src:\
$CORTEX_ROOT/plugins/careful-execution-correlator-plugin/src:\
$CORTEX_ROOT/plugins/static-correlator-plugin/src:\
$CORTEX_ROOT/plugins/watch-service/src:\
$CORTEX_ROOT/adapters/ad-adapter/src:\
$CORTEX_ROOT/adapters/sentinelone-adapter/src:\
$CORTEX_ROOT/adapters/epo-adapter/src:\
$CORTEX_ROOT/adapters/esx-adapter/src:\
$CORTEX_ROOT/devops:\
$CORTEX_ROOT/testing"