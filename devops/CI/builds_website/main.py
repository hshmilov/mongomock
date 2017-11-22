"""A minimal http server for CI purpouses; Allows you to view and control your current machines and docker images."""
import boto3
import traceback
import buildsmanager
import json
from flask import Flask, render_template, jsonify, request

__author__ = "Avidor Bartov"

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
        return jsonify(bm.getImages())
    elif (request.method == "POST"):
        return jsonify(bm.postImageDetails(request.form["repositoryName"], request.form["imageDigest"], request.form))
    elif (request.method == "DELETE"):
        return jsonify(bm.deleteImage(request.form["repositoryName"], request.form["imageDigest"]))


@app.route('/exports', methods=['GET'])
def exports():
    """Return info about our exported vms."""
    return jsonify(bm.getExports())


@app.route('/exports/<key>/url', methods=['GET'])
def export_url(key):
    """Returns a link for a exported ova. Expects to get the key name in the post request."""
    return jsonify(bm.getExportUrl(key))


@app.route('/exports/<key>/manifest', methods=['GET'])
def get_export_manifest(key):
    """Returns a link for a exported ova. Expects to get the key name in the post request."""
    if(request.method == "GET"):
        return jsonify(bm.getExportManifest(key))


@app.route("/exports/<key>", methods=['GET', 'DELETE'])
def export(key):
    """Does all sort of actions on a specific export"""
    if (request.method == "GET"):
        return jsonify(bm.getExports(key=key))
    elif (request.method == "DELETE"):
        return jsonify(bm.deleteExport(key=key))
    else:
        return "Error! Method %s unsupported." % (request.method,), 500


@app.route('/exportsinprogress', methods=['GET'])
def exports_in_progress():
    """Return info about our exported vms."""
    return jsonify(bm.getExportsInProgress())


@app.route("/instances", methods=['GET', 'POST'])
def instances():
    """Return info about ec2."""
    if(request.method == "GET"):
        return jsonify(bm.getInstances())
    elif(request.method == "POST"):
        return jsonify(bm.addInstance(
            request.form["name"],
            request.form["owner"],
            request.form["comments"],
            request.form["configuration_name"],
            request.form["configuration_code"]))
    else:
        return "Error! Method %s unsupported." % (request.method, ), 500


@app.route("/instances/<instance_id>", methods=['GET', 'DELETE', 'POST'])
def instance(instance_id):
    """Get information about instance and provide actions on it."""
    if (request.method == "GET"):
        return jsonify(bm.getInstances(ec2_id=instance_id))

    elif (request.method == "DELETE"):
        return jsonify(bm.terminateInstance(instance_id))

    elif (request.method == "POST"):
        action = request.form["action"]
        if (action == "start"):
            return jsonify(bm.startInstance(ec2_id=instance_id))
        elif (action == "stop"):
            return jsonify(bm.stopInstance(ec2_id=instance_id))
        elif (action == "export"):
            return jsonify(bm.exportInstance(
                ec2_id=instance_id,
                owner=request.form["owner"],
                client_name=request.form["client_name"],
                comments=request.form["comments"]))

    else:
        return return_unsupported()


@app.route("/instances/<instance_id>/manifest", methods=['GET', 'POST'])
@app.route("/instances/<instance_id>/manifest/<manifest_key>", methods=['GET', 'POST'])
def instance_manifest(instance_id, manifest_key=None):
    """Get information about instance and provide actions on it."""
    if (request.method == "GET"):
        return jsonify(bm.getManifest(instance_id, manifest_key))

    elif (request.method == "POST"):
        key = request.form["key"]
        if "value" in request.form:
            # Its a regular form
            value = request.form["value"]
        else:
            # Its a file.
            value = request.files["value"].read().decode("utf-8")

        return jsonify(bm.postManifest(instance_id, key, value))

    else:
        return return_unsupported()


@app.route("/configurations", methods=['GET', 'POST'])
@app.route("/configurations/<object_id>", methods=['GET', 'DELETE', 'POST'])
def configuration(object_id=None):
    """Does all sort of actions on a specific configuration"""
    if (request.method == "GET"):
        return jsonify(bm.getConfigurations())
    elif (request.method == "POST"):
        return jsonify(bm.updateConfiguration(object_id, request.form["name"], request.form["author"], request.form["purpose"], request.form["code"]))
    elif (request.method == "DELETE"):
        return jsonify(bm.deleteConfiguration(object_id))
    else:
        return "Error! Method %s unsupported." % (request.method,), 500


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
