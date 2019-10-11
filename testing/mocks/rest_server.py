"""
HTTPS Flask server for mocking
"""
import ssl
import os
import time
from functools import wraps
from flask import Flask, request, Response, jsonify
from werkzeug.utils import secure_filename

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
APP = Flask('Mock Server')
LOGS = []


def mock_services(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):

        # Some services we want to mock
        sleep = request.args.get('sleep')
        if sleep is not None:
            time.sleep(int(sleep))

        basic_auth_username = request.args.get('basic_auth_username')
        basic_auth_password = request.args.get('basic_auth_password')
        if basic_auth_username is not None and basic_auth_password is not None:
            auth = request.authorization
            if not auth:
                return Response('Please Use Basic Auth', 401,
                                {'WWW-Authenticate': 'Basic realm="Login Required"'})
            if auth.username != basic_auth_username or auth.password != basic_auth_password:
                return Response('Incorrect Basic Auth Credentials', 401,
                                {'WWW-Authenticate': 'Basic realm="Login Required"'})

        return func(*args, **kwargs)

    return func_wrapper


@APP.route('/api/devices/<amount>')
@mock_services
def devices(amount):
    return jsonify([
        {'id': i} for i in range(int(amount))
    ])


@APP.route('/echo/<what>')
@mock_services
def echo(what):
    return what


@APP.route('/error/<return_code>/<content>')
@mock_services
def error_response(return_code, content):
    return Response(str(content), int(return_code))


@APP.route('/headers')
@mock_services
def get_headers():
    return jsonify(dict(request.headers.items()))


@APP.route('/url_params')
@mock_services
def get_url_params():
    return jsonify(dict(request.args.items()))


@APP.route('/body_params', methods=['GET', 'POST'])
@mock_services
def get_body_params():
    json_to_return = request.get_json(silent=True)
    if json_to_return is None:
        json_to_return = {}
    return jsonify(json_to_return)


@APP.route('/logs', methods=['GET', 'POST'])
def logs():
    if request.method == 'POST':
        data = request.get_data()
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        LOGS.append(str(data))
    return jsonify(LOGS)


@APP.route('/https_post', methods=['POST'])
@mock_services
def https_post():
    print(f'Data: {request.get_data()}')
    print(f'Headers: {request.headers}')

    if request.files.get('file'):
        print(f'files: {request.files}')
        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(filename)
    return ''


def main():
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(
        os.path.join(CURRENT_PATH, 'server.crt'),
        os.path.join(CURRENT_PATH, 'server.key'))
    APP.run(threaded=True, host='0.0.0.0', port=33443, ssl_context=context)


if __name__ == '__main__':
    exit(main())
