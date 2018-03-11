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


@app.route('/')
def main():
    """The main path."""
    return render_template("index.html", instances={})  # json.dumps(bm.getInstances()))


@app.route("/images", methods=['GET', 'POST', 'DELETE'])
def images():
    """Returns all docker images."""
    if (request.method == "GET"):
        json_result = (bm.getImages())
    elif (request.method == "POST"):
        json_result = (bm.postImageDetails(request.form["repositoryName"], request.form["imageDigest"], request.form))
    elif (request.method == "DELETE"):
        json_result = (bm.deleteImage(request.form["repositoryName"], request.form["imageDigest"]))

    return jsonify({"result": json_result, "current": bm.getImages()})


@app.route('/exports', methods=['GET'])
def exports():
    """Return info about our exported vms."""
    json_result = (bm.getExports())
    return jsonify({"result": json_result, "current": json_result})


@app.route('/exports/<key>/url', methods=['GET'])
def export_url(key):
    """Returns a link for a exported ova. Expects to get the key name in the post request."""
    json_result = (bm.getExportUrl(key))
    return jsonify({"result": json_result, "current": {}})


@app.route('/exports/<key>/manifest', methods=['GET'])
def get_export_manifest(key):
    """Returns a link for a exported ova. Expects to get the key name in the post request."""
    if(request.method == "GET"):
        json_result = (bm.getExportManifest(key))

    return jsonify({"result": json_result, "current": {}})


@app.route("/exports/<key>", methods=['GET', 'DELETE'])
def export(key):
    """Does all sort of actions on a specific export"""
    if (request.method == "GET"):
        json_result = (bm.getExports(key=key))
    elif (request.method == "DELETE"):
        json_result = (bm.deleteExport(key=key))

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
    """Return info about ec2."""
    if(request.method == "GET"):
        json_result = (bm.getInstances())
    elif(request.method == "POST"):
        json_result = (bm.addInstance(
            request.form["name"],
            request.form["owner"],
            request.form["comments"],
            request.form["configuration_name"],
            request.form["configuration_code"]))

    return jsonify({"result": json_result, "current": bm.getInstances()})


@app.route("/instances/<instance_id>", methods=['GET', 'DELETE', 'POST'])
def instance(instance_id):
    """Get information about instance and provide actions on it."""
    if (request.method == "GET"):
        json_result = (bm.getInstances(ec2_id=instance_id))

    elif (request.method == "DELETE"):
        json_result = (bm.terminateInstance(instance_id))

    elif (request.method == "POST"):
        action = request.form["action"]
        if (action == "start"):
            json_result = (bm.startInstance(ec2_id=instance_id))
        elif (action == "stop"):
            json_result = (bm.stopInstance(ec2_id=instance_id))
        elif (action == "export"):
            json_result = (bm.exportInstance(
                ec2_id=instance_id,
                owner=request.form["owner"],
                client_name=request.form["client_name"],
                comments=request.form["comments"]))

    return jsonify({"result": json_result, "current": bm.getInstances()})


@app.route("/instances/<instance_id>/manifest", methods=['GET', 'POST'])
@app.route("/instances/<instance_id>/manifest/<manifest_key>", methods=['GET', 'POST'])
def instance_manifest(instance_id, manifest_key=None):
    """Get information about instance and provide actions on it."""
    if (request.method == "GET"):
        json_result = (bm.getManifest(instance_id, manifest_key))

    elif (request.method == "POST"):
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
    if (request.method == "GET"):
        json_result = (bm.getConfigurations())
    elif (request.method == "POST"):
        json_result = (bm.updateConfiguration(
            object_id, request.form["name"], request.form["author"], request.form["purpose"], request.form["code"]))
    elif (request.method == "DELETE"):
        json_result = (bm.deleteConfiguration(object_id))

    return jsonify({"result": json_result, "current": bm.getConfigurations()})


@app.route("/install", methods=['GET'])
def get_install_script():
    branch = request.args.get("branch")
    if branch is None:
        branch = "develop"

    return "# how to use: curl -k https://builds.axonius.lan/install[?branch=develop] | bash -\nrm -rf axonius\nmkdir axonius\ncd axonius\ngit init\n# Beware! do not save this token.\ngit pull https://0e28371fe6803ffc7cba318c130a465e9f28d26f@github.com/axonius/cortex {0}\n" \
        "history -c\nhistory -w\ncd install\nchmod 777 *\n./install.sh\nexit\n".format(branch)


@app.route("/install_demo", methods=['GET'])
def get_install_demo_script():
    branch = request.args.get("branch")
    extra_params = request.args.get("exclude")
    if extra_params is None:
        opt_params = ''
    else:
        opt_params = "'--exclude {0}'".format(str(extra_params).replace(',', ' '))
    if branch is None:
        branch = "develop"

    return "# how to use: curl -k https://builds.axonius.lan/install_demo[?branch=develop?exclude=ad,esx,puppet] | bash -\nrm -rf axonius\nmkdir axonius\ncd axonius\ngit init\n# Beware! do not save this token.\ngit pull https://0e28371fe6803ffc7cba318c130a465e9f28d26f@github.com/axonius/cortex {0}\n" \
        "history -c\nhistory -w\ncd install\nchmod 777 *\n./install_demo.sh {1}\nexit\n".format(branch, opt_params)


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
