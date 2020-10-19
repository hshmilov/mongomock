#!/usr/bin/env bash
set -e # from now on exit on any error
source bash_imports.sh

METRICS_SCRIPT_PATH='./plugins/instance_control/get_instance_metrics_linux64'
METRICS_PATH=plugins/instance_control/metrics
PID_FILE=$METRICS_PATH/pid
METRICS_FILE=$METRICS_PATH/metrics.json
RUNNING_INTERVAL=60

mkdir -p $METRICS_PATH

if [[ -f $PID_FILE && -f "/proc/$(cat $PID_FILE)" ]];then
  echo "Get metrics process already running with PID $(cat $PID_FILE)"
  exit 0
fi

if [[ $(uname -r) =~ .*Microsoft || $(uname -s) =~ MINGW.* || "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  METRICS_SCRIPT_PATH='./plugins/instance_control/get_instance_metrics.exe'
else
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # OSX
    METRICS_SCRIPT_PATH='./plugins/instance_control/get_instance_metrics_osx'
  else
    # Linux
    if [ "$(uname -i)" != "x86_64" ];then
      # Linux 32Bit
      METRICS_SCRIPT_PATH='./plugins/instance_control/get_instance_metrics_linux32'
    fi
  fi
fi

if [[ ! -f "$PID_FILE" ]] || ! kill -0 "$(cat $PID_FILE)" > /dev/null 2>&1 ; then
  echo -n $$ > "$PID_FILE"
  while true; do
    $METRICS_SCRIPT_PATH > "$METRICS_FILE"
    sleep "$RUNNING_INTERVAL";
  done
fi