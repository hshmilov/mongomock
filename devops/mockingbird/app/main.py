import os
import traceback

from flask import Flask, send_file, request, jsonify

from mock_manager import MockManager
APP = Flask(__name__)
MM = MockManager('localhost')


@APP.route('/api/devices')
def devices():
    plugin_name = request.args.get('plugin_name')
    client_id = request.args.get('client_id')
    offset = request.args.get('offset')
    limit = request.args.get('limit')

    return jsonify(MM.get_devices(plugin_name, client_id, offset, limit))


@APP.route('/api/users')
def users():
    plugin_name = request.args.get('plugin_name')
    client_id = request.args.get('client_id')
    offset = request.args.get('offset')
    limit = request.args.get('limit')

    return jsonify(MM.get_users(plugin_name, client_id, offset, limit))


@APP.route('/')
def main():
    index_path = os.path.join(APP.static_folder, 'index.html')
    return send_file(index_path)


@APP.errorhandler(Exception)
def all_exception_handler(error):
    """Catch all exceptions and show them in a nice view."""
    return traceback.format_exc().replace('\n', '<br>'), 500


if __name__ == '__main__':
    # Only for debugging while developing
    APP.run(host='0.0.0.0', debug=True, port=80)
