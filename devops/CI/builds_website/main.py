"""A minimal http server for CI purpouses; Allows you to view and control your current machines and docker images."""
import boto3
import traceback
import buildsmanager
import json
from flask import Flask, render_template, jsonify, request

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='/static')
db = None
bm = buildsmanager.BuildsManager()
INSTALL_DEMO_SCRIPT = """# how to use: curl -k https://builds.axonius.lan/install[?fork=axonius&branch=develop&exclude=ad,esx,puppet&set_credentials=true] | bash -
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
cd ..
rm .git*
exit"""

INSTALL_SYSTEM_LINE = "curl -k 'https://builds.axonius.lan/install?fork={fork}&branch={branch}&set_credentials={set_credentials}&include={include}&exclude={exclude}' | bash -"
INSTALL_DEMO_CONFIG = "#!/bin/bash\nset -x\nHOME_DIRECTORY=/home/ubuntu/axonius/install/\nmkdir -p $HOME_DIRECTORY\nLOG_FILE=$HOME_DIRECTORY\"install.log\"\nexec 1>$LOG_FILE 2>&1\n\n{install_system_line}\n\necho Reporting current state to builds server\n\n\nBUILDS_SERVER_URL=\"https://builds.axonius.lan\"\nINSTANCE_ID=$(cat /var/lib/cloud/data/instance-id)\nURL=$(printf \"%s/instances/%s/manifest\" \"$BUILDS_SERVER_URL\" \"$INSTANCE_ID\")\n\ndocker images --digests\ndocker images --digests > $DOCKER_IMAGES_FILE\n\ncurl -k -v -F \"key=docker_images\" -F \"value=@$DOCKER_IMAGES_FILE\" $URL\n\n# we have to copy the install log file and send the copied one, or else problems will happen\n# since this file is open.\ncp $LOG_FILE $LOG_FILE.send\ncurl -k -v -F \"key=install_log\" -F \"value=@$LOG_FILE.send\" $URL\n\necho downloading final manifest from server\ncurl -k $URL > $HOME_DIRECTORY\"manifest.json\"\n\necho final tweeks\nchown -R ubuntu:ubuntu $HOME_DIRECTORY"


@app.route('/')
def main():
    """The main path."""
    return render_template("index.html", instances={})  # json.dumps(bm.getInstances()))


@app.route("/images", methods=['GET', 'POST', 'DELETE'])
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
def exports():
    """Return info about our exported vms."""
    if request.method == "GET":
        json_result = bm.getExports()
    elif request.method == "POST":
        json_result = (bm.export_ova(
            version=request.form["version"],
            owner=request.form["owner"],
            fork=request.form["fork"],
            branch=request.form["branch"],
            client_name=request.form["client_name"],
            comments=request.form["comments"]))

    return jsonify({"result": json_result, "current": json_result})


@app.route('/exports/<key>/url', methods=['GET'])
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
def get_export_manifest(key):
    """Returns a link for a exported ova. Expects to get the key name in the post request."""
    if request.method == "GET":
        json_result = (bm.getExportManifest(key))

    return jsonify({"result": json_result, "current": {}})


@app.route("/exports/<key>", methods=['GET', 'DELETE'])
def export(key):
    """Does all sort of actions on a specific export"""
    if request.method == "GET":
        json_result = (bm.getExports(key=key))
    elif request.method == "DELETE":
        json_result = (bm.deleteExport(version=key))

    return jsonify({"result": json_result, "current": bm.getExports()})


@app.route('/exportsinprogress', methods=['GET'])
def exports_in_progress():
    """Return info about our exported vms."""
    json_result = (bm.getExportsInProgress())

    return jsonify({"result": json_result, "current": json_result})


@app.route('/testinstances', methods=['POST'])
def testinstances():
    """
    Allows to get an already-made and waiting test instance.
    """

    return jsonify({"result": bm.getTestInstance(), "current": {}})


@app.route("/instances", methods=['GET', 'POST'])
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
                                                               include=include, exclude=exclude))

        json_result = (bm.add_instance(
            request.form["name"],
            request.form["owner"],
            config_code,
            request.form["fork"],
            request.form["branch"],
            request.form["public"] == 'true',
            vm_type=instance_type,
        ))

    return jsonify({"result": json_result, "current": bm.getInstances(vm_type=instance_type)})


@app.route("/instances/<instance_id>", methods=['GET', 'DELETE', 'POST'])
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


@app.route("/instances/<instance_id>/manifest", methods=['GET', 'POST'])
@app.route("/instances/<instance_id>/manifest/<manifest_key>", methods=['GET', 'POST'])
def instance_manifest(instance_id, manifest_key=None):
    """Get information about instance and provide actions on it."""
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
    branch = request.args.get("branch", "develop")
    fork = request.args.get("fork", "axonius").split('/')[0]
    set_credentials = "--set-credentials" if request.args.get("set_credentials", False) == "true" else ""
    exclude = request.args.get("exclude")
    include = request.args.get("include")
    if exclude != '':
        exclude = [current_adapter[:-len('_adapter')] for current_adapter in exclude.split(',')]
        opt_params = "'--exclude {0}'".format(' '.join(exclude))
    elif include != '':
        include = [current_adapter[:-len('_adapter')] for current_adapter in include.split(',')]
        opt_params = "'{0}'".format(' '.join(include))
    elif include == '' and exclude == '':
        opt_params = "'--exclude'"

    if branch is None:
        branch = "develop"

    return INSTALL_DEMO_SCRIPT.format(fork=fork, branch=branch, set_credentials=set_credentials,
                                      install_params=opt_params)


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
