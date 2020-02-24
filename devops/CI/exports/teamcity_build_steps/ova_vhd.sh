#!/bin/bash

set -e

PYTHONPATH=devops python3 -u devops/CI/exports/axonius_exports.py --teamcity-step ova_vhd --exports-server-token $TEAMCITY_BUILDS_TOKEN --exports-notifications-url=$EXPORTS_UPDATE_ENDPOINT --teamcity-log "$TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID" --teamcity-owner "$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME" --s3-bucket $S3_BUCKET ova_vhd --qcow3-s3-name $NAME -o output.ova --vhdx-output output.vhdx

function finish {
  rm output.ova output.vhdx
}
trap finish EXIT

PYTHONPATH=devops python3 -u devops/CI/exports/axonius_exports.py --teamcity-step ova_vhd --exports-server-token $TEAMCITY_BUILDS_TOKEN --exports-notifications-url=$EXPORTS_UPDATE_ENDPOINT --teamcity-log "$TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID" --teamcity-owner "$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME" --s3-bucket $S3_BUCKET s3 upload --ova output.ova --vhdx output.vhdx --export-name $NAME


curl -u "$SYSTEM_TEAMCITY_AUTH_USERID:$SYSTEM_TEAMCITY_AUTH_PASSWORD"  -X POST \
  $TEAMCITY_SERVERURL/httpAuth/app/rest/buildQueue \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/xml' \
  -d "<build>
  <triggeringOptions cleanSources=\"true\" rebuildAllDependencies=\"false\" queueAtTop=\"false\"/>
  <buildType id=\"Exports_OvaTestEsx\"/>
   <properties>
        <property name=\"env.startedBy\" value=\"build was triggering from $TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID\"/>
        <property name=\"name\" value=\"$NAME\"/>
        <property name=\"s3bucket\" value=\"$S3_BUCKET\"/>
        <property name=\"teamcity.build.triggeredBy.username\" value=\"$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME\"/>
        <property name=\"branch\" value=\"$BRANCH\"/>
        <property name=\"fork\" value=\"$FORK\"/>
    </properties>
</build>"

