#!/bin/bash

set +o xtrace

set -e

echo "Generating installer files."
echo PYTHONPATH=devops python3 -u devops/CI/exports/axonius_exports.py --teamcity-step installer --exports-server-token $TEAMCITY_BUILDS_TOKEN --exports-notifications-url=$EXPORTS_UPDATE_ENDPOINT --teamcity-log "$TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID" --teamcity-owner "$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME" installer --fork $FORK --branch $BRANCH --name $NAME --output installer.py --git-hash-file git_hash.txt --mode "$MODE"
PYTHONPATH=devops python3 -u devops/CI/exports/axonius_exports.py --teamcity-step installer --exports-server-token $TEAMCITY_BUILDS_TOKEN --exports-notifications-url=$EXPORTS_UPDATE_ENDPOINT --teamcity-log "$TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID" --teamcity-owner "$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME" installer --fork $FORK --branch $BRANCH --name $NAME --output installer.py --git-hash-file git_hash.txt --mode "$MODE"

echo "##teamcity[setParameter name='installer_git_hash' value='`tail -n 1 git_hash.txt`']"

function finish {
  rm installer.py axonius_$NAME.zip
}
trap finish EXIT

echo "Uploading installer files."
PYTHONPATH=devops python3 -u devops/CI/exports/axonius_exports.py --teamcity-step installer --exports-server-token $TEAMCITY_BUILDS_TOKEN --exports-notifications-url=$EXPORTS_UPDATE_ENDPOINT --teamcity-log "$TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID" --teamcity-owner "$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME" --s3-bucket $S3_BUCKET s3 upload --export-name $NAME --installer installer.py --zip axonius_$NAME.zip

echo "Triggering Next teamcity build."
curl -k -u "$SYSTEM_TEAMCITY_AUTH_USERID:$SYSTEM_TEAMCITY_AUTH_PASSWORD"  -X POST \
  $TEAMCITY_SERVERURL/httpAuth/app/rest/buildQueue \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/xml' \
  -d "<build>
  <triggeringOptions cleanSources=\"true\" rebuildAllDependencies=\"false\" queueAtTop=\"false\"/>
  <buildType id=\"Exports_Cloud\"/>
   <properties>
        <property name=\"env.startedBy\" value=\"build was triggering from $TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID\"/>
        <property name=\"name\" value=\"$NAME\"/>
        <property name=\"s3bucket\" value=\"$S3_BUCKET\"/>
        <property name=\"disk_size\" value=\"$DISK_SIZE\"/>
        <property name=\"teamcity.build.triggeredBy.username\" value=\"$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME\"/>
        <property name=\"branch\" value=\"$BRANCH\"/>
        <property name=\"fork\" value=\"$FORK\"/>
        <property name=\"boot_config_script\" value=\"$BOOT_CONFIG_SCRIPT\"/>
        <property name=\"env.ADDITIONAL_EXPORTS_PARAMS\" value=\"$ADDITIONAL_CLOUD_PARAMS\"/>
    </properties>

</build>"

echo "Triggering unencrypted teamcity build."
curl -k -u "$SYSTEM_TEAMCITY_AUTH_USERID:$SYSTEM_TEAMCITY_AUTH_PASSWORD"  -X POST \
  $TEAMCITY_SERVERURL/httpAuth/app/rest/buildQueue \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/xml' \
  -d "<build>
  <triggeringOptions cleanSources=\"true\" rebuildAllDependencies=\"false\" queueAtTop=\"false\"/>
  <buildType id=\"Exports_Cloud\"/>
   <properties>
        <property name=\"env.startedBy\" value=\"build was triggering from $TEAMCITY_SERVERURL/viewLog.html?buildId=$TEAMCITY_BUILD_ID\"/>
        <property name=\"name\" value=\"${NAME}-unencrypted\"/>
        <property name=\"s3bucket\" value=\"$S3_BUCKET\"/>
        <property name=\"disk_size\" value=\"$DISK_SIZE\"/>
        <property name=\"teamcity.build.triggeredBy.username\" value=\"$TEAMCITY_BUILD_TRIGGEREDBY_USERNAME\"/>
        <property name=\"branch\" value=\"$BRANCH\"/>
        <property name=\"fork\" value=\"$FORK\"/>
        <property name=\"boot_config_script\" value=\"$BOOT_CONFIG_SCRIPT\"/>
        <property name=\"env.ADDITIONAL_EXPORTS_PARAMS\" value=\"--unencrypted --installer-s3-name $NAME $ADDITIONAL_CLOUD_PARAMS\"/>
    </properties>

</build>"
