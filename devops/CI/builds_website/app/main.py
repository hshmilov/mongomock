"""A minimal http server for CI purpouses; Allows you to view and control your current machines and docker images."""
import datetime
import time
import traceback
import os
import json

from functools import wraps

from retrying import retry

import tasks

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_dance.contrib.slack import make_slack_blueprint, slack
from flask_dance.consumer import oauth_authorized
from bson import ObjectId

from config import TOKENS_PATH, CREDENTIALS_PATH
from slacknotifier import SlackNotifier
from instancemonitor import MONITORING_BOT_METADATA_NAMESPACE, SHOULD_DELETE_OLD_MESSAGES
from buildsmanager import BuildsManager, LOCAL_BUILDS_HOST
from github import Github

DEFAULT_CLOUD = 'gcp'

SESSION_SECRET_KEY_PATH = os.path.join('..', 'secret.txt')
TIME_TO_SLEEP_BEFORE_ASYNC_RESPONSE = 0    # we wait for async response that require real-time data


class BuildsSettings:
    def __init__(self):
        self.development_mode = os.environ.get('BUILDS_DEBUG') == 'true'
        self.bypass_token = None

        with open(TOKENS_PATH, 'rt') as f:
            self.tokens = json.loads(f.read())

        with open(CREDENTIALS_PATH, 'rt') as f:
            self.credentials = json.loads(f.read())

        with open(SESSION_SECRET_KEY_PATH, 'rt') as f:
            self.secret_key = f.read()

        for token, data in self.tokens.items():
            if data['builds_user_full_name'].lower() == 'builds':
                self.bypass_token = token
                break


class BuildsContext:
    def __init__(self):
        self.bm = BuildsManager()
        self.st = SlackNotifier()
        self.github = Github(
            settings.credentials['github']['data']['username'],
            settings.credentials['github']['data']['password']
        )


def prepare_flask():
    flask_app = Flask(__name__, static_url_path='/static')
    flask_app.config['TEMPLATES_AUTO_RELOAD'] = True
    flask_app.secret_key = settings.secret_key
    blueprint = make_slack_blueprint(
        client_id=settings.credentials['slack']['data']['client_id'],
        client_secret=settings.credentials['slack']['data']['client_secret'],
        scope='identity.basic,identity.email',
    )
    flask_app.register_blueprint(blueprint, url_prefix='/login')

    class BuildsJsonEncoder(json.JSONEncoder):
        # pylint: disable=method-hidden
        def default(self, o):
            if isinstance(o, (ObjectId, datetime.datetime)):
                return str(o)
            return json.JSONEncoder.default(self, o)

    flask_app.json_encoder = BuildsJsonEncoder

    return flask_app


settings = BuildsSettings()
app = prepare_flask()
context = BuildsContext()

INSTALL_DEMO_SCRIPT = """# how to use: curl -k https://builds-local.axonius.lan/api/install[?fork=axonius&branch=develop&exclude=ad,esx,puppet&set_credentials=true] | bash -
set -e
rm -rf /home/ubuntu/cortex
mkdir /home/ubuntu/cortex
cd /home/ubuntu/cortex
git init
# Beware! do not save this token.
git pull https://0e28371fe6803ffc7cba318c130a465e9f28d26f@github.com/{fork}/cortex {branch}
./devops/scripts/host_installation/init_host.sh
cd install
chmod 777 *
# Notice that this raises the system in debug mode (all ports are opened outside and files are mounted from the outside of the system).
# The public up has only port 443 open but the private one is completely open.
# This is done this way for getting the credentials of the raised adapters (more precisely to query the core register endpoint to get registered adapters.
# This should be changed in the future when the system matures for security reasons and others.
./install.sh {install_params} --clean --run-system {set_credentials}
cd /home/ubuntu/cortex
rm .git*
chown -R ubuntu:ubuntu *
if [ "{run_cycle}" == "True" ]; then
    source prepare_python_env.sh
    python devops/scripts/discover_now.py
fi
exit"""

INSTALL_SYSTEM_LINE = "curl -k 'https://{builds_host}/api/install?fork={fork}&branch={branch}&set_credentials={set_credentials}&include={include}&exclude={exclude}&run_cycle={run_cycle}&system_up_params={system_up_params}' | bash -"
STARTUP_SCRIPT_TEMPLATE = """#!/bin/bash
set -x
HOME_DIRECTORY=/home/ubuntu/builds_log/
mkdir -p $HOME_DIRECTORY
LOG_FILE=$HOME_DIRECTORY"install.log"
exec 1>$LOG_FILE 2>&1
echo prepend domain-name-servers 192.168.20.4\; >> /etc/dhcp/dhclient.conf
echo prepend domain-search \\"axonius.lan\\"\; >> /etc/dhcp/dhclient.conf
dhclient -v
{install_system_line}
{post_script}
chown -R ubuntu:ubuntu $HOME_DIRECTORY
chown -R ubuntu:ubuntu /home/ubuntu/cortex
"""


def authorize(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not slack.authorized:

            if settings.development_mode:
                session['builds_user_full_name'] = settings.tokens['Development']['builds_user_full_name']
                session['builds_user_id'] = settings.tokens['Development']['builds_user_id']  # Avidor's slack id
            elif 'x-auth-token' in request.headers and request.headers['x-auth-token'] in settings.tokens:
                session['builds_user_full_name'] = settings.tokens[request.headers['x-auth-token']]['builds_user_full_name']
                session['builds_user_id'] = settings.tokens[request.headers['x-auth-token']]['builds_user_id']
            else:
                return render_template('login.html', slack_login_url=url_for("slack.login"))

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
    return render_template('index.html', username=session['builds_user_full_name'])


@app.route('/api/exports', methods=['GET', 'POST'])
@authorize
def exports():
    """Return info about our exported vms."""
    if request.method == 'GET':
        limit = int(request.args.get('limit', '0'))
        json_result = context.bm.get_exports(limit=limit)
        # We can't return the log, its too much data. we return it only by a specific key request.
        for export_raw in json_result:
            export_raw.pop('log', None)

        return jsonify({'result': json_result})

    if request.method == 'POST':
        json_result = (context.bm.export_ova(
            version=request.form['version'],
            owner=(session['builds_user_full_name'], session['builds_user_id']),
            fork=request.form['fork'],
            branch=request.form['branch'],
            client_name=request.form.get('client_name', ''),
            comments=request.form['comments']))

        return jsonify({'result': json_result})


@app.route('/api/exports/<key>/status', methods=['POST', 'GET'])
@authorize
def set_export_status(key):
    """Returns a link for an exported ova. Expects to get the key name in the post request."""

    json_result = dict()

    if request.method == 'GET':
        json_result = context.bm.get_export_running_log(key)
    elif request.method == 'POST':
        status = request.form['status']
        git_hash = request.form['git_hash']

        json_result = (
            context.bm.update_export_status(
                key,
                'completed' if int(status) == 0 else 'failed', git_hash
            )
        )

    return jsonify({'result': json_result, 'current': {}})


@app.route('/api/exports/<key>', methods=['GET', 'DELETE'])
@authorize
def export_by_key(key):
    """Does all sort of actions on a specific export"""
    if request.method == 'DELETE':
        json_result = context.bm.delete_export(version=key)
        return jsonify({'result': json_result, 'current': context.bm.get_exports()})
    elif request.method == 'GET':
        return jsonify({'result': context.bm.get_export_by_version(key)})


@app.route('/api/exports/<key>/log', methods=['GET'])
@authorize
def export_log_by_key(key):
    """Does all sort of actions on a specific export"""
    return context.bm.get_export_by_version(key)['log'].replace('\n', '<br>')


@app.route('/api/exportsinprogress', methods=['GET'])
@authorize
def exports_in_progress():
    """Return info about our exported vms."""
    json_result = context.bm.get_exports_in_progress()
    return jsonify({'result': json_result, 'current': json_result})


@app.route('/api/instances', methods=['GET', 'POST'])
@authorize
def instances():
    if request.method == 'GET':
        vm_type = request.args.get('vm_type')
        return jsonify({'result': context.bm.get_instances(vm_type=vm_type)})
    elif request.method == 'POST':
        data = request.get_json()
        instance_name = data['name']
        instance_type = data['type']
        vm_type = data['vm_type']
        key_name = data.get('key_name')
        instance_cloud = data.get('cloud') or DEFAULT_CLOUD
        instance_image = data.get('image')
        is_public = data.get('public') is True
        num = int(data.get('num')) if data.get('num') else 1
        config = data.get('config') or {}

        config_code = None
        post_script = config.get('post_script') or ''
        if instance_image is None:
            if config.get('empty') is True:
                config_code = STARTUP_SCRIPT_TEMPLATE.format(install_system_line='', post_script=post_script)

            elif config.get('custom_code'):
                config_code = STARTUP_SCRIPT_TEMPLATE.format(
                    install_system_line=config.get('custom_code'),
                    post_script=post_script
                )

            else:
                adapters = config['adapters']
                should_run_all = 'ALL' in adapters
                if should_run_all:
                    adapters.remove('ALL')

                exclude = ','.join(adapters) if should_run_all else ''
                include = ','.join(adapters) if not should_run_all else ''

                config_code = STARTUP_SCRIPT_TEMPLATE.format(install_system_line=INSTALL_SYSTEM_LINE.format(
                    builds_host=LOCAL_BUILDS_HOST,
                    fork=config['fork'],
                    branch=config['branch'],
                    set_credentials='true' if config.get('set_credentials') is True else 'false',
                    include=include, exclude=exclude,
                    run_cycle=False,
                    system_up_params='--prod'), post_script=post_script
                )

        user_auth = (session['builds_user_full_name'], session['builds_user_id'])

        task = tasks.add_instances.delay(
            instance_cloud,
            vm_type,
            instance_name,
            instance_type,
            num,
            instance_image,
            key_name,
            is_public,
            config_code,
            config.get('network_security_options'),
            user_auth,
            config.get('fork'),
            config.get('branch')
        )
        result = dict()
        is_async = request.args.get('async') and request.args.get('async').lower() == 'true'
        if is_async:
            result['action_id'] = task.id
            task.forget()
        else:
            generic, group_name = task.get()
            result.update({'instances': generic, 'group_name': group_name})

        if request.args.get('get_new_data') and request.args.get('get_new_data').lower() == 'true':
            if is_async:
                time.sleep(TIME_TO_SLEEP_BEFORE_ASYNC_RESPONSE)
            result['result'] = context.bm.get_instances()

        return jsonify(result)


@app.route("/api/instances/<cloud>", methods=['GET', 'DELETE', 'POST'])
@authorize
def instances_per_cloud(cloud):
    return jsonify({'result': context.bm.get_instances(cloud=cloud)})


@app.route("/api/instances/<cloud>/<instance_id>", methods=['GET'])
@authorize
def instance(cloud, instance_id):
    return jsonify({'result': context.bm.get_instances(cloud=cloud, instance_id=instance_id)})


@app.route("/api/instances/<cloud>/<instance_id>/<action>", methods=['POST'])
@authorize
def instance_action(cloud, instance_id, action):
    """Get information about instance and provide actions on it."""
    if action == 'delete':
        task = tasks.terminate_instance.delay(cloud=cloud, instance_id=instance_id)

    elif action == 'start':
        task = tasks.start_instance.delay(cloud=cloud, instance_id=instance_id)

    elif action == 'stop':
        task = tasks.stop_instance.delay(cloud=cloud, instance_id=instance_id)

    elif action == 'bot_monitoring':
        instance_data = context.bm.get_instances(cloud=cloud, instance_id=instance_id)[0]
        owner = instance_data['db']['owner']
        instance_name = instance_data['db']['name']

        context.bm.change_bot_monitoring_status(cloud, instance_id, request.form["status"])

        if request.form['status'] == 'false':
            word = 'disabled'
        else:
            word = 'enabled'

        context.st.post_channel(
            f'owner "{owner}" has *{word}* bot monitoring for instance "{instance_name}"',
            attachments=[context.st.get_instance_attachment(instance_data, [])]
        )
        task = None
    else:
        raise ValueError('Not supported')

    result = dict()
    is_async = request.args.get('async') and request.args.get('async').lower() == 'true'
    if task:
        if is_async:
            result['action_id'] = task.id
            task.forget()
        else:
            action_result = task.get()
            result.update({'action': action_result})

    if request.args.get('get_new_data') and request.args.get('get_new_data').lower() == 'true':
        if is_async and task:
            time.sleep(TIME_TO_SLEEP_BEFORE_ASYNC_RESPONSE)
        result['result'] = context.bm.get_instances()

    return jsonify(result)


# This is not authorized on purpose
@app.route('/api/instances/<cloud>/<instance_id>/update_state',  methods=['GET'])
def instance_update_state(cloud, instance_id):
    """ Set the status of the bot monitoring"""
    state = request.args.get('state')
    assert state in ['keep', 'shutdown', 'terminate']

    instance_data = context.bm.get_instances(cloud=cloud, instance_id=instance_id)[0]
    instance_name = instance_data['db']['name']
    owner = instance_data['db']['owner']
    owner_slack_id = instance_data['db']['owner_slack_id']
    vm_state = instance_data['cloud']['state']
    last_message_channel = instance_data['db'].get('monitoring_bot', {}).get('bot_last_message_channel')
    last_message_ts = instance_data['db'].get('monitoring_bot', {}).get('bot_last_message_ts')
    attachment = context.st.get_instance_attachment(instance_data, [])

    try:
        if last_message_channel and last_message_ts and SHOULD_DELETE_OLD_MESSAGES:
            context.st.delete_message(last_message_channel, last_message_ts)
    except Exception:
        context.st.post_channel(f'Could not delete last message for instance "{instance_name}"')

    context.st.post_channel(
        f'Owner "{owner}" has marked instance "{instance_name}" as {state}',
        attachments=[attachment]
    )

    try:
        if state == 'keep':
            if vm_state not in ['running', 'stopping', 'pending', 'stopped']:
                context.st.post_user(owner_slack_id, f'Can not keep your instance, it is not there anymore!',
                                     attachments=[attachment])
            else:
                context.st.post_user(owner_slack_id, f'Ok, I\'m *keeping* it.', attachments=[attachment])
        elif state == "shutdown":
            if vm_state != 'running':
                context.st.post_user(owner_slack_id, f'Can not stop your instance, it is not running!.',
                                     attachments=[attachment])
            else:
                tasks.stop_instance.delay(cloud, instance_id).forget()
                context.st.post_user(owner_slack_id, f'Ok, I\'m *stopping* it.', attachments=[attachment])
        elif state == 'terminate':
            if vm_state not in ['running', 'stopping', 'stopped']:
                context.st.post_user(owner_slack_id, f'Can not terminate your instance, it is not there anymore!',
                                     attachments=[attachment])
            else:
                tasks.terminate_instance.delay(cloud, instance_id).forget()
                context.st.post_user(owner_slack_id, f'Ok, I\'m *terminating* it.', attachments=[attachment])

    except Exception as e:
        context.st.post_channel(f'problem with instance {instance_id}: {repr(e)}')

    # Delete instance metadata
    context.bm.set_instance_metadata(cloud, instance_id, MONITORING_BOT_METADATA_NAMESPACE, {})

    # Update user interaction. This should happen in shutdown and terminate but not in keep.
    context.bm.update_last_user_interaction_time(cloud, instance_id)

    return render_template('message.html', message='Done. Check your slack for final message')


@app.route("/api/groups/delete", methods=['POST'])
@authorize
def delete_groups():
    group_name = request.get_json()['group_name']
    task = tasks.terminate_group.delay(group_name)
    json_result = dict()

    is_async = request.args.get('async') and request.args.get('async').lower() == 'true'
    if is_async:
        json_result['action_id'] = task.id
        task.forget()
    else:
        json_result['terminate'] = task.get()

    if request.args.get('get_new_data') and request.args.get('get_new_data').lower() == 'true':
        if is_async:
            time.sleep(TIME_TO_SLEEP_BEFORE_ASYNC_RESPONSE)
        json_result['result'] = context.bm.get_instances()
    return jsonify(json_result)


@app.route('/api/install', methods=['GET'])
def get_install_demo_script():
    # Unauthorized since machines use it
    branch = request.args.get('branch', 'develop')
    fork = request.args.get('fork', 'axonius').split('/')[0]
    set_credentials = '--set-credentials' if request.args.get('set_credentials', False) == 'true' else ''
    exclude = request.args.get('exclude')
    include = request.args.get('include')
    run_cycle = request.args.get('run_cycle', '') == 'True'
    opt_params = '\''
    opt_params += request.args.get('system_up_params', '') if include == '' else ''

    if exclude != '':
        opt_params += " --exclude {0}'".format(' '.join(exclude.split(',')))
    elif include != '':
        opt_params += "{0} ".format(' '.join(include.split(',')))
        opt_params += request.args.get('system_up_params', '') + '\''
    elif include == '' and exclude == '':
        opt_params += " --exclude'"

    if branch is None:
        branch = 'develop'

    return INSTALL_DEMO_SCRIPT.format(fork=fork, branch=branch, set_credentials=set_credentials,
                                      install_params=opt_params, run_cycle=str(run_cycle))


@app.route('/api/github')
@authorize
@retry(stop_max_attempt_number=2, wait_fixed=100)
def github_get_general_data():
    main_repo = context.github.get_repo('axonius/cortex')

    return jsonify({
        'branches': [branch.name for branch in main_repo.get_branches()],
        'tags': [tag.name for tag in main_repo.get_tags()],
        'forks': [repo.full_name for repo in main_repo.get_forks()]
    })


@app.route('/api/github/branches')
@authorize
@retry(stop_max_attempt_number=2, wait_fixed=100)
def github_get_branches_for_fork():
    main_repo = context.github.get_repo(request.args['fork'])
    return jsonify({
        'branches': [branch.name for branch in main_repo.get_branches()]
    })


@app.route('/api/github/adapters')
@authorize
@retry(stop_max_attempt_number=2, wait_fixed=100)
def github_get_adapters_for_branch():
    fork = request.args['fork']
    branch = request.args['branch']

    adapters = [
        file.path.split('/')[-1].replace('_service.py', '') for file in
        context.github.get_repo(fork).get_contents('testing/services/adapters', branch)
        if '__init__' not in file.path.lower()
    ]

    return jsonify({'adapters': adapters})


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


@app.errorhandler(Exception)
def all_exception_handler(error):
    """Catch all exceptions and show them in a nice view."""
    return traceback.format_exc().replace("\n", "<br>"), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', threaded=True)
