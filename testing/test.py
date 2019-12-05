"""
Handles running all scenarios of tests.
"""
# pylint: disable=too-many-branches, too-many-statements, too-many-locals
import glob
import io
import socket
import sys
import os
import subprocess
import argparse
import concurrent.futures
import threading
import tarfile
import time
from collections import OrderedDict

from typing import Tuple, List, Dict, Callable

from builds import Builds
from builds.builds_factory import BuildsInstance
from testing.test_helpers.ci_helper import TeamcityHelper


DEFAULT_CLOUD_INSTANCE_CLOUD = 'aws'
DEFAULT_CLOUD_INSTANCE_TYPE = 't2.2xlarge'
DEFAULT_CLOUD_NUMBER_OF_INSTANCES = 10
DEFAULT_MAX_PARALLEL_TESTS_IN_INSTANCE = 5
BUILDS_GROUP_NAME_ENV = 'BUILDS_GROUP_NAME'
MAX_PARALLEL_PREPARE_CI_ENV_JOBS = 10   # prepare_ci_env is a very resource-consuming task, we have to limit it
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARTIFACTS_DIR_RELATIVE = 'artifacts'
ARTIFACTS_DIR_ABSOLUTE = os.path.join(ROOT_DIR, ARTIFACTS_DIR_RELATIVE)
ARTIFACTS_DIRS_INSIDE_CONTAINER = {
    'logs': '/home/ubuntu/cortex/logs',
    'screenshots': '/home/ubuntu/cortex/screenshots',
}
DIR_MAP = {
    'integ': os.path.join('testing', 'tests'),
    'parallel': os.path.join('testing', 'parallel_tests'),
    'ui': os.path.join('testing', 'ui_tests', 'tests')
}
# The following line contains commands that we run before each new test. we are going to append more commands
# to it later, hence we have ./prepare_python_env.sh (for these commands)
FIRST_BASH_COMMANDS_BEFORE_EACH_TEST = 'set -e; source ./prepare_python_env.sh; ./clean_dockers.sh; '
MAX_SECONDS_FOR_ONE_JOB = 60 * 120  # no job (test / bunch of jobs) should take more than that
MAX_SECONDS_FOR_THREAD_POOL = 60 * 180  # Just an extra caution for a timeout
TC = TeamcityHelper()


def execute(commands, cwd=None, timeout=None, stream_output: bool=False):
    if not isinstance(commands, list):
        commands = ['/bin/bash', '-c', commands]

    if stream_output is False:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    else:
        stdout = None
        stderr = None

    subprocess_handle = subprocess.Popen(commands, stdout=stdout, stderr=stderr, cwd=cwd)

    try:
        stdout, stderr = subprocess_handle.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess_handle.kill()
        if stream_output is False:
            stdout, stderr = subprocess_handle.communicate()
        raise ValueError(f'subprocess "{commands}" timed-out after {timeout} seconds, \n'
                         f'stdout: {stdout.decode("utf-8")}\nstderr: {stderr.decode("utf-8")}')

    if subprocess_handle.returncode != 0:
        raise ValueError(f'subprocess "{commands}" returned rc {subprocess_handle.returncode}, \n'
                         f'stdout: {stdout.decode("utf-8")} \nstderr: {stderr.decode("utf-8")}')

    if stdout is None or stderr is None:
        return None
    return stdout.decode('utf-8'), stderr.decode('utf-8')


def tp_execute(list_of_execs: List[Tuple[Callable, Tuple, Dict, object]], tp_instances: int):
    with concurrent.futures.ThreadPoolExecutor(max_workers=tp_instances) as executor:
        futures_to_data = {executor.submit(data[0], *data[1], **data[2]): (data[3], time.time())
                           for data in list_of_execs}
        for future in concurrent.futures.as_completed(futures_to_data, timeout=MAX_SECONDS_FOR_THREAD_POOL):
            exec_identification, start_time = futures_to_data[future]
            try:
                ret = future.result()
                yield exec_identification, ret, time.time() - start_time
            except Exception as e:
                TC.print(f'Error with execution {str(exec_identification)} after {time.time() - start_time} '
                         f'seconds: {str(e)}')
                raise


class InstanceManager:
    def __init__(self, cloud, instance_type, number_of_instances):
        self.cloud = cloud
        self.instance_type = instance_type
        self.number_of_instances = number_of_instances
        self.__instances: List[BuildsInstance] = []
        self.__builds = Builds()
        self.__group_name = None

        execute(f'rm -rf {ARTIFACTS_DIR_ABSOLUTE}')
        if not os.path.exists(ARTIFACTS_DIR_ABSOLUTE):
            os.makedirs(ARTIFACTS_DIR_ABSOLUTE)

    @staticmethod
    def __ssh_execute(instance, job_name, commands, timeout=MAX_SECONDS_FOR_ONE_JOB, append_ts=True):
        assert isinstance(commands, str), 'ssh execute command must be a shell command'
        assert '"' not in commands, 'Not supported'
        commands = f'/bin/bash -c "{commands}"'
        if append_ts:
            commands = f'{commands} | ts -s'  # ts to print timestamp
        if timeout > 0:
            commands = f'timeout --signal=SIGTERM --kill-after=30 {timeout} {commands}'
        commands = f'set -o pipefail; {commands}'   # In any way, rc should fail on pipes transfer
        TC.print(f'{instance}: executing {job_name}: {commands}')
        start_time = time.time()

        rc, output = instance.ssh(commands)  # a timeout is implemented using the timeout command.
        end_time = time.time()
        if rc != 0:
            if (end_time - start_time) > timeout:
                raise ValueError(f'Error, instance {instance} with job {job_name} and commands {commands} '
                                 f'timeout and was killed with SIGKILL. Output is {output}')
            raise ValueError(f'Error, instance {instance} with job {job_name} and '
                             f'commands {commands} returned rc {rc}: {output}')

        return output

    def __execute_ssh_on_all(self, job_name, command, max_parallel=None, **kwargs):
        """
        Executes a command, in parallel, on all instances.
        :param job_name: the job name
        :param command: the bash command to execute.
        :param max_parallel: The amount of parallel executions we can have, None for unlimited.
        :return:
        """
        what_to_run = [
            (
                self.__ssh_execute,
                (instance, job_name, command),
                kwargs,
                instance
            ) for instance in self.__instances]
        yield from tp_execute(what_to_run, max_parallel or len(self.__instances))

    def __put_file_in_all_instances(self, local_path, remote_path):
        """
        Copies a local path to a remote destination on all instances
        :param local_path: the local path of a tar file
        :param remote_path: the remote path in which the tar file will be extracted
        :return:
        """

        def copy_and_open_tar(instance: BuildsInstance, file_local_path, file_remote_path):
            with open(file_local_path, 'rb') as f:
                instance.put_file(f, file_remote_path)

        what_to_run = [
            (
                copy_and_open_tar,
                (instance, local_path, remote_path),
                {},
                instance
            ) for instance in self.__instances
        ]

        yield from tp_execute(what_to_run, len(self.__instances))

    def prepare_all(self, group_name):
        """
        Creates {number_of_instances} independent cloud instances and prepares the system on them.
        :return:
        """
        self.__group_name = group_name
        if self.cloud == 'gcp':
            cloud = self.__builds.CloudType.GCP
        elif self.cloud == 'aws':
            cloud = self.__builds.CloudType.AWS
        else:
            raise ValueError(f'Invalid cloud {self.cloud}')

        self.__instances, group_name_from_builds = self.__builds.create_instances(
            group_name,
            self.instance_type,
            self.number_of_instances,
            instance_cloud=cloud
        )
        TC.set_environment_variable(BUILDS_GROUP_NAME_ENV, group_name_from_builds)

        for instance in self.__instances:
            print(f'Waiting for instance {instance} to initialize...')
            instance.wait_for_ssh()

        for instance_name, ret, overall_time in \
                self.__execute_ssh_on_all('Initialize the cortex environment',
                                          'rm -rf /home/ubuntu/cortex; mkdir /home/ubuntu/cortex; ls -lah /home/ubuntu',
                                          append_ts=False):
            with TC.block(f'content of {instance_name}:/home/ubuntu'):
                print(ret)

        # Create a copy of the source code and copy it to there.
        print(f'Creating source code tar and copying it..')
        execute('rm -rf cortex.tar')
        execute('shopt -s dotglob; tar cjf cortex.tar --exclude venv --exclude __pycache__ '
                '--exclude .idea --exclude logs --exclude .cache *')

        print(f'Transfering cortex.tar to all instances..')
        list(self.__put_file_in_all_instances(os.path.abspath('cortex.tar'), '/home/ubuntu/cortex/cortex.tar'))
        print(f'Unpacking cortex.tar..')
        list(
            self.__execute_ssh_on_all(
                'Untar tar file', 'cd /home/ubuntu/cortex; tar -xjf cortex.tar', append_ts=False)
        )

        for instance_name, ret, overall_time in \
                self.__execute_ssh_on_all('show files on axonius', 'whoami; ls -lah /home/ubuntu', append_ts=False):
            with TC.block(f'content of {instance_name}:/home/ubuntu'):
                print(ret)

        print(f'Source code copying complete, installing Axonius..')
        execute('rm cortex.tar')

        # init host.
        for instance_name, ret, overall_time in self.__execute_ssh_on_all(
                'Init host',
                'cd /home/ubuntu/cortex/; sudo ./devops/scripts/host_installation/init_host.sh',
                append_ts=False
        ):
            with TC.block(f'Finished init_host on {instance_name}, took {overall_time} seconds'):
                print(ret)

        # Since we just installed docker, re-connect.
        for instance in self.__instances:
            instance.wait_for_ssh()

        # Build everything.
        for instance_name, ret, overall_time in self.__execute_ssh_on_all(
                'Prepare ci env with caching of images',
                'cd /home/ubuntu/cortex/; ./prepare_ci_env.sh --cache-images'
        ):
            with TC.block(f'Finished building axonius on {instance_name}, took {overall_time} seconds'):
                print(ret)

    def terminate_all(self):
        print(f'Terminating all instances..')
        self.__builds.terminate_all()

    def execute_jobs(self, jobs: Dict):
        """
        Executes the test jobs defined in jobs.
        :param jobs: a dict of job_name: job_val, each job_val is a string is the bash commands we need to run.
        :return:
        """
        free_instances = self.__instances.copy()
        free_instances_lock = threading.Lock()
        tests_statistics = []
        tests_with_exceptions = []
        last_exception = ValueError('General Error')
        jobs_left = jobs.copy()

        def execute_on_next_free_instance(command_job_name, command):
            # Do note this function runs in different threads and thus should be thread-safe in terms of printing.
            # We use the flow-id feature of teamcity to achieve this.
            start_time = time.time()
            with free_instances_lock:
                instance_to_run_on = free_instances.pop()

            try:
                current_output = self.__ssh_execute(instance_to_run_on, command_job_name, command)
            except Exception as e:
                current_output = e

            # Create the test artifacts folder
            if not os.path.exists(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name)):
                os.makedirs(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name))

            if not os.path.exists(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name, 'xml')):
                os.makedirs(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name, 'xml'))

            # Start putting artifacts in this folder
            try:
                current_logs_tar_file_name = f'{command_job_name}_logs.tar.gz'
                logs_tar_file_location = os.path.join(
                    ARTIFACTS_DIR_ABSOLUTE, command_job_name, current_logs_tar_file_name)
                with open(logs_tar_file_location, 'wb') as tar_file_obj:
                    tar_file_obj.write(instance_to_run_on.get_folder_as_tar(ARTIFACTS_DIRS_INSIDE_CONTAINER['logs']))

                # Now extract the xml files which have the tests result and report them as well
                with tarfile.open(logs_tar_file_location, mode='r') as tar_file:
                    for xml_path in [xml_file_path for xml_file_path in tar_file.getnames() if
                                     xml_file_path.endswith('.xml')]:
                        with tar_file.extractfile(xml_path) as extracted_xml_file:
                            final_xml_file_name = os.path.split(xml_path)[1]
                            with open(os.path.join(ARTIFACTS_DIR_ABSOLUTE,
                                                   command_job_name,
                                                   'xml',
                                                   final_xml_file_name
                                                   ), 'wb') \
                                    as final_xml:
                                final_xml.write(extracted_xml_file.read())
            except Exception as e:
                TC.print(f'{instance_to_run_on}: job {command_job_name} exception while getting logs. '
                         f'Current output is:\n{current_output}. Exception is: {str(e)}')
                raise

            # Try getting screenshots. If we are in parallel tests this might fail
            try:
                screenshots_tar_file = instance_to_run_on.get_folder_as_tar(
                    ARTIFACTS_DIRS_INSIDE_CONTAINER['screenshots']
                )

                # Also all the screenshots
                with tarfile.open(fileobj=io.BytesIO(screenshots_tar_file)) as tar_file:
                    tar_file.extractall(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name))
            except AssertionError:
                # This is legitimate, we do not always have screenshots.
                pass

            with free_instances_lock:
                free_instances.append(instance_to_run_on)

            return instance_to_run_on, current_output, time.time() - start_time

        for (job_name, ret, total_time_including_waiting_and_getting_artifacts) in tp_execute(
                [
                    (
                        execute_on_next_free_instance,
                        (job_name, job_val, ),
                        {},
                        job_name
                    ) for job_name, job_val in jobs.items()
                ],
                len(free_instances)
        ):
            ret_instance_name, output, overall_time = ret
            overall_time_nice = time.strftime('%H:%M:%S', time.gmtime(overall_time))
            test_summary = f'Finished with job {job_name} on {ret_instance_name} after {overall_time_nice}'
            tests_statistics.append(test_summary)
            print(test_summary)
            jobs_left.pop(job_name)
            print(f'Jobs left: {jobs_left.keys()}')
            with TC.block(f'job {job_name} ({overall_time_nice})'):
                with TC.block('output'):
                    print(str(output))  # output could also be of type Exception
                    if isinstance(output, Exception):
                        tests_with_exceptions.append(job_name)
                        last_exception = output
                # We need to publish the job_name folder but if we specify job_name it will publish only
                # its internal contents. To avoid it we simply publish the whole artifacts folder, which is fine
                # because teamcity is smart and caches uploads so it doesn't re-upload it.
                TC.publishArtifacts(ARTIFACTS_DIR_RELATIVE)
                TC.importData('junit', os.path.join(ARTIFACTS_DIR_RELATIVE, job_name, 'xml'))

                # publish tests metadata. wait 3 seconds to give teamcity the option to parse the xml data
                # otherwise it will not find the test since teamcity did not parse it.
                time.sleep(3)
                for pic_id, png_relative_path in \
                        enumerate(glob.iglob(os.path.join(ARTIFACTS_DIR_RELATIVE, job_name, '**', '*.png'),
                                             recursive=True)):
                    test_name = os.path.basename(os.path.dirname(png_relative_path))
                    # We need to set a path relative to the artifacts folder, so we need to remove it from the png
                    # relative path.
                    TC.set_image_attachment(
                        f'pytest: {test_name}',
                        png_relative_path[len(ARTIFACTS_DIR_RELATIVE + os.path.sep):],
                        name=f'pic_{pic_id}'
                    )

        print(f'Finished, below are all tests with the time they took, ordered by the time of run')
        for i, message in enumerate(tests_statistics):
            print(f'{i}. {message}', flush=True)

        # If there was at least one exception we should exit.
        if len(tests_with_exceptions) > 0:
            # An exception in the code should fail the script, otherwise the test could pass.
            # Note that this is something that should bearly happen (it indicates problems in the CI, not in the
            # tests)
            sys.stderr.write(f'The following exceptions happened: {tests_with_exceptions}\n')
            sys.stderr.flush()
            # Raise the last exception to make it appear in the test and fail it.
            raise last_exception


def get_list_of_tests_in_path(path):
    output, _ = execute('pytest --collect-only', cwd=path)

    # we have to extract the path, this will look like:
    # <Module 'plugins/static_users_correlator/tests/test_static_users_correlator.py'>
    modules_raw = [line[9:-2] for line in output.splitlines() if line.startswith('<Module ')]
    return modules_raw


def main():
    parser = argparse.ArgumentParser(usage='''
    Specific examples of using this script
    test run all -> runs all tests on this host.
    test run all -d -> runs all tests on this host, distributed. This will run as much Axonius system as possible on 
                        this host.
    test run parallel -p test_aws.py::test_fetch_devices -> runs this specific test.
    test run ut -p axonius-libs/tests/test_async.py -> runs this specific module.
    test run ui -p test_bad_login.py -> runs this specific module.
    ''')
    parser.add_argument('action', choices=['run', 'delete'])
    parser.add_argument('target', choices=['all', 'ut', 'integ', 'parallel', 'ui'], help='Which scenario to run')
    parser.add_argument('-p', '--path', help='In case of running a specific test, this would be the path')
    parser.add_argument('--cloud', choices=['aws', 'gcp'], default=DEFAULT_CLOUD_INSTANCE_CLOUD, help='type of cloud')
    parser.add_argument('--number-of-instances', type=int, default=DEFAULT_CLOUD_NUMBER_OF_INSTANCES,
                        help='Number of instances in the cloud for parallelized work')
    parser.add_argument('--instance-type', default=DEFAULT_CLOUD_INSTANCE_TYPE, help='instance type, e.g. t2.2xlarge')
    parser.add_argument('--max-parallel-builder-tasks', type=int, default=DEFAULT_MAX_PARALLEL_TESTS_IN_INSTANCE,
                        help='Set the amount of max jobs in the parallel builder (which can be run distributed). '
                             'This should be used only for debugging')
    parser.add_argument('--pytest-args', nargs='*', help='Extra args to pass to pytest, with a -- prefix.')
    parser.add_argument('--pytest-single-args', nargs='*', help='Extra single args to pass to pytest, with a - prefix.')

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    extra_pytest_args = ' '.join([f'--{arg}' for arg in args.pytest_args]) if args.pytest_args else ''
    extra_pytest_single_args = \
        ' '.join([f'-{arg}' for arg in args.pytest_single_args]) \
        if args.pytest_single_args \
        else ''
    all_extra_pytest_args = f'{extra_pytest_args} {extra_pytest_single_args}'

    print(f'Cloud type: {args.cloud}')
    print(f'Number of instances: {args.number_of_instances}')
    print(f'Instance Type: {args.instance_type}')
    print(f'Max Parallel Builder Tasks: {args.max_parallel_builder_tasks}')
    print(f'Extra pytest arguments: {extra_pytest_args}')
    print(f'Extra pytest single arguments: {extra_pytest_single_args}')

    group_name = os.environ['BUILD_NUMBER'] if 'BUILD_NUMBER' in os.environ else f'Local test ({socket.gethostname()})'
    # test_group_name_as_env = group_name.replace('"', '-').replace('$', '-').replace('#', '-')

    if args.action == 'run':
        instance_manager = InstanceManager(args.cloud, args.instance_type, args.number_of_instances)
        try:
            instance_manager.prepare_all(group_name)
            print(f'Is running under teamcity: {TC.is_in_teamcity()}')

            def get_ut_tests_jobs():
                return {
                    'Unit Tests': f'./run_ut_tests.sh {all_extra_pytest_args}'
                }

            def get_integ_tests_jobs():
                integ_tests = get_list_of_tests_in_path(os.path.join(ROOT_DIR, DIR_MAP['integ']))
                with TC.block('Collected integration tests modules'):
                    for test_module in integ_tests:
                        print(test_module)

                return {
                    'integ_' + file_name.split('.py')[0]:
                        f'python3 -u '
                        f'./testing/run_pytest.py {all_extra_pytest_args} {os.path.join(DIR_MAP["integ"], file_name)}'
                    for file_name in integ_tests
                }

            def get_parallel_tests_jobs():
                parallel_tests = get_list_of_tests_in_path(os.path.join(ROOT_DIR, DIR_MAP['parallel']))
                with TC.block('Collected parallel tests modules'):
                    for test_module in parallel_tests:
                        print(test_module)

                parallel_jobs = dict()
                for i in range(0, len(parallel_tests), args.max_parallel_builder_tasks):
                    job_name = 'parallel_' + '_'.join([
                        file_path.split('.py')[0]
                        for file_path in parallel_tests[i:i + args.max_parallel_builder_tasks]
                    ])

                    files_list = ' '.join([
                        os.path.join(DIR_MAP['parallel'], file_path)
                        for file_path in parallel_tests[i:i + args.max_parallel_builder_tasks]
                    ])

                    parallel_jobs[job_name] = \
                        f'python3 -u ./testing/run_parallel_tests.py {all_extra_pytest_args} {files_list}'

                return parallel_jobs

            def get_ui_tests_jobs():
                ui_tests = get_list_of_tests_in_path(os.path.join(ROOT_DIR, DIR_MAP['ui']))

                slow_modules = ['test_instances_after_join.py',
                                'test_instances_before_join.py',
                                'test_instances_upgrade.py']
                for slow in slow_modules[:]:
                    if slow in ui_tests:
                        ui_tests.remove(slow)
                    else:
                        print(f'{slow} is not found in slow_modules!')
                        slow_modules.remove(slow)
                ui_tests = slow_modules + ui_tests

                with TC.block('Collected ui tests modules'):
                    for test_module in ui_tests:
                        print(test_module)

                return {
                    'ui_' + test_module.split('.py')[0]:
                        'python3 -u ./testing/run_ui_tests.py '
                        f'{all_extra_pytest_args} {os.path.join(DIR_MAP["ui"], test_module)}'
                    for test_module in ui_tests
                }

            jobs = OrderedDict()
            # Collect jobs. Run UI first since they are the longest
            if args.target in ['ui', 'all']:
                jobs.update(get_ui_tests_jobs())
            if args.target in ['ut', 'all']:
                jobs.update(get_ut_tests_jobs())
            if args.target in ['integ', 'all']:
                jobs.update(get_integ_tests_jobs())
            if args.target in ['parallel', 'all']:
                jobs.update(get_parallel_tests_jobs())

            with TC.block(f'Jobs for target {args.target}'):
                for job_name, job_value in jobs.items():
                    print(f'{job_name}: {job_value}')

            bash_commands_before_each_test = FIRST_BASH_COMMANDS_BEFORE_EACH_TEST
            for artifact_dir in ARTIFACTS_DIRS_INSIDE_CONTAINER.values():
                bash_commands_before_each_test += 'rm -rf ' + os.path.join(artifact_dir, '*') + '; '

            for job_name in jobs:
                jobs[job_name] = f'cd cortex; {bash_commands_before_each_test} {jobs[job_name]}'
            instance_manager.execute_jobs(jobs)

        finally:
            instance_manager.terminate_all()
    elif args.action == 'delete':
        group_name = os.environ.get(BUILDS_GROUP_NAME_ENV)
        if group_name:
            print(f'Trying to terminate instances group {group_name}')
            try:
                Builds().terminate_group(group_name)
                print('Terminated successfully')
            except Exception as e:
                print(f'Could not terminate group {group_name}: {e}')


if __name__ == '__main__':
    sys.exit(main())
