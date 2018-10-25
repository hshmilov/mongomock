"""A minimal http server for CI purpouses; Allows you to view and control your current machines and docker images."""
import traceback
import os
from functools import wraps
from slacknotifier import SlackNotifier
from instancemonitor import MONITORING_BOT_METADATA_NAMESPACE, InstanceMonitor, SHOULD_DELETE_OLD_MESSAGES

import buildsmanager

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_dance.contrib.slack import make_slack_blueprint, slack
from flask_dance.consumer import oauth_authorized

NORMAL_EC2_TYPE = "t2.medium"
STRONG_EC2_TYPE = "t2.xlarge"

DEVELOPMENT_MODE = False


# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='/static')
app.secret_key = "supersekrit"
blueprint = make_slack_blueprint(
    client_id=os.environ['SLACK_LOGIN_APP_CLIENT_ID'],
    client_secret=os.environ['SLACK_LOGIN_APP_CLIENT_SECRET'],
    scope=["identity.basic"],
)
app.register_blueprint(blueprint, url_prefix="/login")

db = None
bm = buildsmanager.BuildsManager()
st = SlackNotifier(os.environ['SLACK_WORKSPACE_APP_BOT_API_TOKEN'], 'builds')
INSTALL_DEMO_SCRIPT = """# how to use: curl -k https://builds-local.axonius.lan/install[?fork=axonius&branch=develop&exclude=ad,esx,puppet&set_credentials=true] | bash -
rm -rf axonius
mkdir axonius
cd axonius
git init
# Beware! do not save this token.
git pull https://0e28371fe6803ffc7cba318c130a465e9f28d26f@github.com/{fork}/cortex {branch}
history -c
history -w
cd install
chmod 777 *
# Notice that this raises the system in debug mode (all ports are opened outside and files are mounted from the outside of the system).
# The public up has only port 443 open but the private one is completely open.
# This is done this way for getting the credentials of the raised adapters (more precisely to query the core register endpoint to get registered adapters.
# This should be changed in the future when the system matures for security reasons and others.
./install.sh {install_params} --clean --run-system {set_credentials}
cd /axonius
rm .git*
if [ "{run_cycle}" == "True" ]; then
    source prepare_python_env.sh
    python devops/scripts/discover_now.py
fi
exit"""

INSTALL_SYSTEM_LINE = "curl -k 'https://builds-local.axonius.lan/install?fork={fork}&branch={branch}&set_credentials={set_credentials}&include={include}&exclude={exclude}&run_cycle={run_cycle}' | bash -"
INSTALL_DEMO_CONFIG = "#!/bin/bash\nset -x\nHOME_DIRECTORY=/home/ubuntu/axonius/install/\nmkdir -p $HOME_DIRECTORY\nLOG_FILE=$HOME_DIRECTORY\"install.log\"\nexec 1>$LOG_FILE 2>&1\n\n{install_system_line}\n\necho Reporting current state to builds server\n\n\nBUILDS_SERVER_URL=\"https://builds-local.axonius.lan\"\nINSTANCE_ID=$(cat /var/lib/cloud/data/instance-id)\nURL=$(printf \"%s/instances/%s/manifest\" \"$BUILDS_SERVER_URL\" \"$INSTANCE_ID\")\n\ndocker images --digests\ndocker images --digests > $DOCKER_IMAGES_FILE\n\ncurl -k -v -F \"key=docker_images\" -F \"value=@$DOCKER_IMAGES_FILE\" $URL\n\n# we have to copy the install log file and send the copied one, or else problems will happen\n# since this file is open.\ncp $LOG_FILE $LOG_FILE.send\ncurl -k -v -F \"key=install_log\" -F \"value=@$LOG_FILE.send\" $URL\n\necho downloading final manifest from server\ncurl -k $URL > $HOME_DIRECTORY\"manifest.json\"\n\necho final tweeks\nchown -R ubuntu:ubuntu $HOME_DIRECTORY"


def authorize(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not slack.authorized:
            if DEVELOPMENT_MODE:
                session['builds_user_full_name'] = 'Development'
                session['builds_user_id'] = 'U6CU068S0'  # Avidor's slack id
            else:
                return render_template("login.html", slack_login_url=url_for("slack.login"))

        return f(*args, **kwargs)
    return decorated_function


@oauth_authorized.connect
def logged_in(blueprint, token):
    # Get the username and full name
    resp = slack.post("users.identity").json()
    session['builds_user_full_name'] = resp['user']['name']
    session['builds_user_id'] = resp['user']['id']


@app.route('/logout')
def logout():
    if slack.authorized:
        slack.post("auth.revoke")
        del app.blueprints['slack'].token
        del session['builds_user_full_name']
        del session['builds_user_id']

    return redirect("/")


@app.route('/')
@authorize
def main():
    """The main path."""
    return render_template("index.html", username=session['builds_user_full_name'])


@app.route("/images", methods=['GET', 'POST', 'DELETE'])
@authorize
def images():
    """Returns all docker images."""
    if request.method == "GET":
        json_result = (bm.getImages())
    elif request.method == "POST":
        json_result = (bm.postImageDetails(request.form["repositoryName"], request.form["imageDigest"], request.form))
    elif request.method == "DELETE":
        json_result = (bm.deleteImage(request.form["repositoryName"], request.form["imageDigest"]))

    return jsonify({"result": json_result, "current": bm.getImages()})


@app.route('/exports', methods=['GET', 'POST'])
@authorize
def exports():
    """Return info about our exported vms."""
    if request.method == "GET":
        json_result = bm.getExports()
    elif request.method == "POST":
        json_result = (bm.export_ova(
            version=request.form["version"],
            owner=(session['builds_user_full_name'], session['builds_user_id']),
            fork=request.form["fork"],
            branch=request.form["branch"],
            client_name=request.form["client_name"],
            comments=request.form["comments"]))

    return jsonify({"result": json_result, "current": json_result})


@app.route('/exports/<key>/url', methods=['GET'])
@authorize
def export_url(key):
    """Returns a link for a exported ova. Expects to get the key name in the post request."""
    json_result = (bm.getExportUrl(key))
    return jsonify({"result": json_result, "current": {}})


@app.route('/exports/<export_identifier>/status', methods=['POST', 'GET'])
def set_export_status(export_identifier):
    """Returns a link for a exported ova. Expects to get the key name in the post request."""

    if request.method == "GET":
        json_result = bm.get_export_running_log(export_identifier)
    else:
        status = request.form["status"]
        log = request.files["log"].read().decode("utf-8")

        json_result = (bm.update_export_status(export_identifier, "completed" if int(status) == 0 else "failed", log))

    return jsonify({"result": json_result, "current": {}})


@app.route('/exports/<key>/manifest', methods=['GET'])
@authorize
def get_export_manifest(key):
    """Returns a link for a exported ova. Expects to get the key name in the post request."""
    if request.method == "GET":
        json_result = (bm.getExportManifest(key))

    return jsonify({"result": json_result, "current": {}})


@app.route("/exports/<key>", methods=['GET', 'DELETE'])
@authorize
def export(key):
    """Does all sort of actions on a specific export"""
    if request.method == "GET":
        json_result = (bm.getExports(key=key))
    elif request.method == "DELETE":
        json_result = (bm.deleteExport(version=key))

    return jsonify({"result": json_result, "current": bm.getExports()})


@app.route('/exportsinprogress', methods=['GET'])
@authorize
def exports_in_progress():
    """Return info about our exported vms."""
    json_result = (bm.getExportsInProgress())

    return jsonify({"result": json_result, "current": json_result})


@app.route('/testinstances', methods=['POST'])
@authorize
def testinstances():
    """
    Allows to get an already-made and waiting test instance.
    """

    return jsonify({"result": bm.getTestInstance(), "current": {}})


@app.route("/instances", methods=['GET', 'POST'])
@authorize
def instances():
    instance_type = request.args.get("instance_type")

    """Return info about ec2."""
    if request.method == "GET":
        json_result = (bm.getInstances(vm_type=instance_type))
    elif request.method == "POST":
        adapters = request.form["adapters"].split(',')
        should_run_all = "ALL" in adapters
        if should_run_all:
            adapters.remove('ALL')
        exclude = ','.join(adapters) if should_run_all else ''
        include = ','.join(adapters) if not should_run_all else ''

        if request.form.get("empty", False) == 'true':
            config_code = INSTALL_DEMO_CONFIG.format(install_system_line='')

        else:
            config_code = INSTALL_DEMO_CONFIG.format(
                install_system_line=INSTALL_SYSTEM_LINE.format(fork=request.form["fork"], branch=request.form["branch"],
                                                               set_credentials=request.form.get("set_credentials",
                                                                                                'false'),
                                                               include=include, exclude=exclude,
                                                               run_cycle=instance_type == "Demo-VM"))

        ec2_type = request.form["ec2_type"]
        if ec2_type == "normal":
            ec2_type = NORMAL_EC2_TYPE
        elif ec2_type == "strong":
            ec2_type = STRONG_EC2_TYPE
        else:
            raise ValueError("Got unsupported ec2 type")

        json_result = (bm.add_instance(
            request.form["name"],
            (session['builds_user_full_name'], session['builds_user_id']),
            ec2_type,
            config_code,
            request.form["fork"],
            request.form["branch"],
            request.form["public"] == 'true',
            vm_type=instance_type
        ))

    return jsonify({"result": json_result, "current": bm.getInstances(vm_type=instance_type)})


@app.route("/instances/<instance_id>", methods=['GET', 'DELETE', 'POST'])
@authorize
def instance(instance_id):
    """Get information about instance and provide actions on it."""
    if request.method == "GET":
        json_result = (bm.getInstances(ec2_id=instance_id))

    elif request.method == "DELETE":
        json_result = (bm.terminateInstance(instance_id))

    elif request.method == "POST":
        action = request.form["action"]
        if action == "start":
            json_result = (bm.startInstance(ec2_id=instance_id))
        elif action == "stop":
            json_result = (bm.stopInstance(ec2_id=instance_id))

    return jsonify({"result": json_result, "current": bm.getInstances()})


@app.route("/instances/<instance_id>/bot_monitoring",  methods=['POST'])
@authorize
def instance_bot_monitoring(instance_id):
    """ Set the status of the bot monitoring"""
    instance = bm.getInstances(ec2_id=instance_id)[0]
    owner = instance['db']['owner']
    instance_name = instance['db']['name']
    attachment = InstanceMonitor.get_instance_attachment(instance, [])

    status = bm.changeBotMonitoringStatus(instance_id, request.form["status"])

    if request.form["status"] == 'false':
        word = 'disabled'
    else:
        word = 'enabled'

    st.post_channel(f'owner "{owner}" has *{word}* bot monitoring for instance "{instance_name}"',
                    attachments=[attachment])
    return jsonify({"result": status, "current": bm.getInstances()})


# This is not authorized on purpose
@app.route("/instances/<instance_id>/update_state",  methods=['GET'])
def instance_update_state(instance_id):
    """ Set the status of the bot monitoring"""
    state = request.args.get("state")
    assert state in ["keep", "shutdown", "terminate"]

    instance = bm.getInstances(ec2_id=instance_id)[0]
    instance_name = instance['db']['name']
    owner = instance['db']['owner']
    owner_slack_id = instance['db']['owner_slack_id']
    vm_state = instance['ec2']['state']
    last_message_channel = instance['db'].get('monitoring_bot', {}).get('bot_last_message_channel')
    last_message_ts = instance['db'].get('monitoring_bot', {}).get('bot_last_message_ts')
    attachment = InstanceMonitor.get_instance_attachment(instance, [])

    try:
        if last_message_channel and last_message_ts and SHOULD_DELETE_OLD_MESSAGES:
            st.delete_message(last_message_channel, last_message_ts)
    except Exception:
        st.post_channel(f'Could not delete last message for instance "{instance_name}"')

    st.post_channel(f'Owner "{owner}" has marked instance "{instance_name}" as {state}', attachments=[attachment])

    try:
        if state == 'keep':
            if vm_state not in ['running', 'stopping', 'stopped']:
                st.post_user(owner_slack_id, f'Can not keep your instance, it is not there anymore!',
                             attachments=[attachment])
            else:
                st.post_user(owner_slack_id, f'Ok, I\'m *keeping* it.', attachments=[attachment])
        elif state == "shutdown":
            if vm_state != 'running':
                st.post_user(owner_slack_id, f'Can not stop your instance, it is not running!.',
                             attachments=[attachment])
            else:
                bm.stopInstance(instance_id)
                st.post_user(owner_slack_id, f'Ok, I\'m *stopping* it.', attachments=[attachment])
        elif state == 'terminate':
            if vm_state not in ['running', 'stopping', 'stopped']:
                st.post_user(owner_slack_id, f'Can not terminate your instance, it is not there anymore!',
                             attachments=[attachment])
            else:
                bm.terminateInstance(instance_id)
                st.post_user(owner_slack_id, f'Ok, I\'m *terminating* it.', attachments=[attachment])

    except Exception as e:
        st.post_channel(f'problem with instance {instance_id}: {repr(e)}')

    # Delete instance metadata
    bm.set_instance_metadata(instance_id, MONITORING_BOT_METADATA_NAMESPACE, {})

    # Update user interaction. This should happen in shutdown and terminate but not in keep.
    bm.update_last_user_interaction_time(instance_id)

    return render_template("message.html", message="Done. Check your slack for final message")


@app.route("/instances/<instance_id>/manifest", methods=['GET', 'POST'])
@app.route("/instances/<instance_id>/manifest/<manifest_key>", methods=['GET', 'POST'])
def instance_manifest(instance_id, manifest_key=None):
    """Get information about instance and provide actions on it.
    does not requires auth to make it possible for installation scripts to post to it
    """
    if request.method == "GET":
        json_result = (bm.getManifest(instance_id, manifest_key))

    elif request.method == "POST":
        key = request.form["key"]
        if "value" in request.form:
            # Its a regular form
            value = request.form["value"]
        else:
            # Its a file.
            value = request.files["value"].read().decode("utf-8")

        json_result = (bm.postManifest(instance_id, key, value))

    return jsonify({"result": json_result, "current": {}})


@app.route("/configurations", methods=['GET', 'POST'])
@app.route("/configurations/<object_id>", methods=['GET', 'DELETE', 'POST'])
@authorize
def configuration(object_id=None):
    """Does all sort of actions on a specific configuration"""
    if request.method == "GET":
        json_result = (bm.getConfigurations())
    elif request.method == "POST":
        json_result = (bm.updateConfiguration(
            object_id, request.form["name"], request.form["author"], request.form["purpose"], request.form["code"]))
    elif request.method == "DELETE":
        json_result = (bm.deleteConfiguration(object_id))

    return jsonify({"result": json_result, "current": bm.getConfigurations()})


@app.route("/install", methods=['GET'])
def get_install_demo_script():
    # Unauthorized since machines use it
    branch = request.args.get("branch", "develop")
    fork = request.args.get("fork", "axonius").split('/')[0]
    set_credentials = "--set-credentials" if request.args.get("set_credentials", False) == "true" else ""
    exclude = request.args.get("exclude")
    include = request.args.get("include")
    run_cycle = request.args.get("run_cycle", '') == 'True'
    if exclude != '':
        opt_params = "'--exclude {0}'".format(' '.join(exclude.split(',')))
    elif include != '':
        opt_params = "'{0}'".format(' '.join(include.split(',')))
    elif include == '' and exclude == '':
        opt_params = "'--exclude'"

    if branch is None:
        branch = "develop"

    return INSTALL_DEMO_SCRIPT.format(fork=fork, branch=branch, set_credentials=set_credentials,
                                      install_params=opt_params, run_cycle=str(run_cycle))


@app.after_request
def add_header(r):
    """
    Disables caching.

    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


def return_unsupported():
    """Returns an error message to the user."""
    return "Error! Method %s unsupported." % (request.method, ), 500


@app.errorhandler(Exception)
def all_exception_handler(error):
    """Catch all exceptions and show them in a nice view."""
    return traceback.format_exc().replace("\n", "<br>"), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
