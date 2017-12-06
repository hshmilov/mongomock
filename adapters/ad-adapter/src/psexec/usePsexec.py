"""usePsexec.py: Python script to enable some basic psexec commands.
   Works only on python 2.x !!!
"""
__author__ = "Ofir Yefet"

# TODO: Check on ubuntu!
# TODO: Change the service path to something else
# TODO: Add the option to insert service path in the run_exe function
# TODO: remove prints and use exit codes (dont ever throw errors)

import sys

import psexec
import argparse
import time
from argparse import Namespace

# TODO: Should change this paths according to what we decide
DEFAULT_SERVICE_PATH = ("ExecuteSvc/Release/ExecuteSvc.exe")
DEFAULT_REMOTE_EXE_PATH = "AxonProcess.exe"
DEFAULT_REMOTE_RESULT_PATH = "axoniusCommandResult.txt"
DEFAULT_REMOTE_TEMP_RESULT_PATH = "axoniusCommandResultTemp.txt"
DEFAULT_REMOTE_CONFIG_PATH = "axon_instructions.cfg"


def get_file(psObj, args):
    psObj.get_file(args.remote_path, args.local_path)
    return 0


def send_file(psObj, args):
    psObj.send_file(args.local_path, args.remote_path)
    return 0


def run_service(psObj, args):
    if 'service_path' in args:
        psObj.execute_service(args.service_path)
    else:
        psObj.execute_service(DEFAULT_SERVICE_PATH)
    return 0


def run_exe(psObj, args):
    _delete_files_from_remmote(psObj, [DEFAULT_REMOTE_EXE_PATH])

    # Uploading the new exe file with our magic name
    send_file(psObj, Namespace(
        remote_path=DEFAULT_REMOTE_EXE_PATH, local_path=args.exe_path))
    run_service(psObj, {})
    return 0


def _alter_config_file_for_shell(config_path):
    # Reading the command content
    config_file = open(config_path, 'r')
    command = config_file.read()
    config_file.close()

    # Writing to the same file in order to create a conf file
    config_file = open(config_path, 'w')
    config_file.write('cmd;' + command)
    config_file.close()


def _delete_files_from_remmote(psObj, files):
    for file_path in files:
        try:
            psObj.delete_file(file_path)
        except psexec.fileExistsException:
            pass


def run_shell(psObj, args):
    _delete_files_from_remmote(psObj, [DEFAULT_REMOTE_EXE_PATH,
                                       DEFAULT_REMOTE_CONFIG_PATH])

    _alter_config_file_for_shell(args.config_path)
    # Uploading the config file containing our shell command
    send_file(psObj, Namespace(
        remote_path=DEFAULT_REMOTE_CONFIG_PATH, local_path=args.config_path))

    # Running the service (It will look for the config file in the remote sytem)
    run_service(psObj, {})

    get_result = 1
    execution_time = time.time()
    time.sleep(5)  # Sleeping a bit to let the command start
    # Waiting 30 seconds for the file to appear
    while (get_result != 0) or time.time() - execution_time > 30:
        try:
            get_result = get_file(psObj, Namespace(
                remote_path=DEFAULT_REMOTE_RESULT_PATH, local_path=args.result_path))
        except Exception as e:
            pass
        time.sleep(5)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',
                        required=True,
                        help='The address of the wanted device',
                        dest='addr')

    parser.add_argument('--username',
                        required=True,
                        help='The username of an admin user',
                        dest='username')

    parser.add_argument('--password',
                        required=True,
                        help='Password of the admin user',
                        dest='password')

    parser.add_argument('--domain',
                        required=True,
                        help='The domain of the issued device',
                        dest='domain')

    subparser = parser.add_subparsers()

    sp_start = subparser.add_parser('getfile',
                                    help='Getting file from remote computer. type -h for help')
    sp_start.add_argument('--remote',
                          required=True,
                          help='The remote path of the file we want to get (Inside the Windows folder)',
                          dest="remote_path")
    sp_start.add_argument('--local',
                          required=True,
                          help='The local path for the file to be saved',
                          dest="local_path")
    sp_start.set_defaults(which=get_file)

    sp_start = subparser.add_parser(
        'sendfile', help='Sending file to remote computer. type -h for help')
    sp_start.add_argument('--remote',
                          required=True,
                          help='The remote path for the file to be saved',
                          dest="remote_path")
    sp_start.add_argument('--local',
                          required=True,
                          help='The local path of the wanted file',
                          dest="local_path")
    sp_start.set_defaults(which=send_file)

    sp_start = subparser.add_parser(
        'runservice', help='Getting file from remote computer. type -h for help')
    sp_start.add_argument('--servicepath',
                          help='The remote path for the file to be saved',
                          dest="service_path")
    sp_start.set_defaults(which=run_service)

    sp_start = subparser.add_parser(
        'runexe', help='Running Exe file on the remote computer')
    sp_start.add_argument('--exepath',
                          required=True,
                          help='The remote path for the file to execute',
                          dest="exe_path")
    sp_start.set_defaults(which=run_exe)

    sp_start = subparser.add_parser(
        'runshell', help='Running shell command on the remote computer')
    sp_start.add_argument('--command_path',
                          required=True,
                          help='a file containing the command',
                          dest="config_path")
    sp_start.add_argument('--result_path',
                          required=True,
                          help='The local path for the result file to be saved',
                          dest="result_path")
    sp_start.set_defaults(which=run_shell)

    try:
        args = parser.parse_args()
    except Exception as e:
        sys.exit("Couldnt parse args, reason: {0}".format(str(e)))

    if not hasattr(args, 'which'):
        parser.print_help()
        sys.exit("Couldnt find which attribute")

    try:
        psObj = psexec.PSEXEC(username=args.username,
                              password=args.password, domain=args.domain)
        psObj._init_connection(args.addr)

        return_value = args.which(psObj, args)
        sys.exit(return_value)  # Success
    except Exception as e:
        sys.exit("Error while trying to perform {0}. Reason: {1}".format(
            str(args.which), str(e)))


if __name__ == '__main__':
    sys.exit(main())
