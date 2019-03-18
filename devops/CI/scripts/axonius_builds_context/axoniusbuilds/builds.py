"""
Does everything.
"""
import os

import paramiko
import requests
import urllib3

# surpress warning messages about vaildation error
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# its debug by default
IS_DEBUG = True
DEFAULT_SECURITY_GROUP = 'sg-8e00dce6'
BUILDS_AUTO_TEST_VM_TYPE = 'Auto-Test-VM'
BUILDS_AUTH_TOKEN = 'c9129428-1973-45e2-94e2-8cca92a31350'
STRONG_EC2_TYPE = "strong"
NORMAL_EC2_TYPE = "normal"


def debugprint(print_str):
    if IS_DEBUG is True:
        print('[+] {0}'.format(print_str))


# Get the location of this directory, to be able to open files relatively.
__location__ = os.path.join(os.getcwd(), os.path.dirname(__file__))


def restreq(method, resource, *args, **kwargs):
    """
    Connects to https://builds.axonius.local and returns a json formatted result.

    :param method: GET, POST, DELETE, etc.
    :param resource: whatever is after the first slash. images, exports, etc.
    :param data: an object with key-value of data. i.e. {repository: 'repname', 'key2': 'value2'}
    :return: a json of formatted data.
    """
    headers = kwargs.pop('headers', {})

    headers['x-auth-token'] = BUILDS_AUTH_TOKEN

    data = requests.request(method, 'https://builds-local.axonius.lan/{0}'.format(resource), verify=False, headers=headers, *args,
                            **kwargs)
    if data.status_code > 299 or data.status_code < 200:
        raise ValueError('Error! Got status code {0} with data: {1}'.format(data.status_code, data.text))
    return data.json()


class Instance:
    """
    A single instance.
    """

    def __init__(self, name, fork='axonius', branch='develop', ami=None):
        self.name = name
        if ami is None:
            self.fork = fork
            self.branch = branch
        self.ami = ami

    def new_server(self):
        if self.ami is None:
            params = {'name': self.name, 'fork': self.fork,
                      'branch': self.branch, 'security_group': DEFAULT_SECURITY_GROUP, 'ec2_type': NORMAL_EC2_TYPE}
        else:
            params = {'name': self.name, 'image_id': self.ami, 'security_group': DEFAULT_SECURITY_GROUP,
                      'ec2_type': STRONG_EC2_TYPE}
        result = restreq('POST', 'instances', data=params, params={'instance_type': BUILDS_AUTO_TEST_VM_TYPE})['result']
        return result['instance_id']

    def __enter__(self):
        self.instance_id = self.new_server()
        self.node_url = 'instances/{0}'.format(self.instance_id)
        self.info = restreq('GET', self.node_url, params={'instance_type': BUILDS_AUTO_TEST_VM_TYPE})['result'][0]
        self.name = self.info['db']['name']
        self.ip = self.info['ec2']['private_ip_address']

        self.debug_print('New vm instance {0} created with ip {1}'.format(self.instance_id, self.ip))

        self.sshc = paramiko.SSHClient()
        self.sshc.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # if we cant ssh connect at least terminate.
        try:
            self.initialize_ssh()
            return self
        except Exception as exc:
            self.terminate()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()

    def initialize_ssh(self, key_file_path=None, password=None):
        num_tries = 0
        connected = False

        # We try to connect numerous of times, because it takes time until a new instance is ready.
        while connected is False:
            try:
                self.debug_print('Trying to ssh.. (attempt {0})'.format(num_tries))
                k = None if key_file_path is None else paramiko.RSAKey.from_private_key_file(key_file_path)
                self.sshc.connect(self.ip, username='ubuntu', password=password, pkey=k, timeout=60, auth_timeout=60)
                connected = True
            except (TimeoutError, paramiko.SSHException, paramiko.ssh_exception.NoValidConnectionsError) as exc:
                num_tries += 1
                if num_tries == 50:
                    raise
            except Exception as exc:
                if exc.args[0] == 'timed out':
                    num_tries += 1
                    if num_tries == 50:
                        raise
                else:
                    raise

        self.debug_print('Connected via SSH.')

    # pylint: disable=keyword-arg-before-vararg
    def ssh(self, command, quiet=True, *args, **kwargs):
        """
        Runs a command and returns its output. not interactive.
        :param quiet: Should not write debug print.
        :param command: the command.
        :return: (stdout, stderr).
        """

        if not quiet:
            self.debug_print('Running ssh: {0}'.format(command))
        _, stdout, stderr = self.sshc.exec_command(command, *args, **kwargs)

        final_stdout_arr = []
        final_stderr_arr = []

        # Print stdout. we do this instead of stderr to see it while its happening.
        for line in stdout:
            line = line
            if not quiet:
                self.debug_print('STDOUT: {0}'.format(line).rstrip())
            final_stdout_arr.append(line)

        # And now, stderr.
        for line in stderr:
            line = line
            if not quiet:
                self.debug_print('STDERR: {0}'.format(line).rstrip())
            final_stderr_arr.append(line)

        return '\n'.join(final_stdout_arr), '\n'.join(final_stderr_arr)

    def debug_print(self, print_string):
        debugprint('[{0}] {1}'.format(self.name, print_string))

    def terminate(self):
        self.debug_print('Terminating...')
        return restreq('DELETE', self.node_url)['result']
