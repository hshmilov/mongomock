import subprocess
import time
import os

from scripts.watchdog.watchdog_task import WatchdogTask

SLEEP_SECONDS = 60 * 5
SCRIPT_TIMEOUT = 120
FILES_DIR = os.path.join(os.path.dirname(__file__), '..', 'files')
REMOVE_VETH_FILE = os.path.abspath(os.path.join(FILES_DIR, 'remove_veth_interfaces.sh'))


def _execute(subprocess_arguments):
    """
    Generically executes a subprocess for execution needs
    :param subprocess_arguments: a list of strings to pass to subprocess
    :return: the stdout of this process
    """
    # Running the command.
    subprocess_handle = subprocess.Popen(subprocess_arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Checking if return code is zero, if not, it will raise an exception
    try:
        command_stdout, command_stderr = subprocess_handle.communicate(
            timeout=SCRIPT_TIMEOUT)
    except subprocess.TimeoutExpired:
        # The child process is not killed if the timeout expires, so in order to cleanup properly a well-behaved
        # application should kill the child process and finish communication (from python documentation)
        subprocess_handle.kill()
        command_stdout, command_stderr = subprocess_handle.communicate()
        command_stdout = command_stdout.decode('utf-8')
        command_stderr = command_stderr.decode('utf-8')
        raise ValueError(f'Execution timeout! output: {command_stdout}, \nstderr: {command_stderr}')
    except Exception as e:
        raise ValueError(f'Generic error: {str(e)}')

    if subprocess_handle.returncode != 0:
        raise ValueError(f'Error - Return code is {subprocess_handle.returncode}\n'
                         f'stdout: {command_stdout}\nstderr: {command_stderr}')

    return f'stdout:{command_stdout.strip()}\nstderr:{command_stderr.strip()}'


class RemoveDeadVethTask(WatchdogTask):
    def run(self):
        while True:
            self.report_info(f'{self.name} is running')
            try:
                if os.geteuid() != 0:
                    self.report_error('This script should run as root, continuing')
                self.report_info(_execute([REMOVE_VETH_FILE]))
            except Exception as e:
                self.report_error(f'Error - could not run remove veth script: {str(e)}')

            time.sleep(SLEEP_SECONDS)


if __name__ == '__main__':
    gw = RemoveDeadVethTask()
    gw.start()
