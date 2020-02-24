#!/bin/bash

set -e

PYTHONPATH=devops python3 -u devops/CI/exports/axonius_exports.py --teamcity-step cloud --exports-server-token $TEAMCITY_BUILDS_TOKEN --exports-notifications-url=$EXPORTS_UPDATE_ENDPOINT --teamcity-log "$TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID" --teamcity-owner "$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME" cloud --installer-s3-name $NAME --name $NAME $ADDITIONAL_EXPORTS_PARAMS --qcow-output output.qcow3

function finish {
  rm output.qcow3
}
trap finish EXIT

PYTHONPATH=devops python3 -u devops/CI/exports/axonius_exports.py --teamcity-step cloud --exports-server-token $TEAMCITY_BUILDS_TOKEN --exports-notifications-url=$EXPORTS_UPDATE_ENDPOINT --teamcity-log "$TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID" --teamcity-owner "$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME" --s3-bucket $S3_BUCKET s3 upload --export-name $NAME --qcow3 output.qcow3

