"""
Handles running all scenarios of tests.
"""
# pylint: disable=too-many-branches, too-many-statements, too-many-locals
import glob
import io
import sys
import os
import subprocess
import argparse
import concurrent.futures
import threading
import tarfile
import time
import socket

from typing import Tuple, List, Dict, Callable

import psutil
import docker

from testing.test_helpers.ci_helper import TeamcityHelper


DEFAULT_AXONIUS_INSTANCE_RAM_IN_GB = 32
DEFAULT_MAX_PARALLEL_TESTS_IN_INSTANCE = 5
MAX_PARALLEL_PREPARE_CI_ENV_JOBS = 10   # prepare_ci_env is a very resource-consuming task, we have to limit it
GB_NEEDED_FOR_GRID = 4
GB_NEEDED_FOR_CHROME_INSTANCE = 2
AXONIUS_INSTANCES_PREFIX = 'axonius-'
SELENIUM_INSTANCE_PREFIX = 'selenium-'
AXONIUS_HOST_IMAGE_TAG = 'axonius/axonius-host-image'
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARTIFACTS_DIR_RELATIVE = 'artifacts'
ARTIFACTS_DIR_ABSOLUTE = os.path.join(ROOT_DIR, ARTIFACTS_DIR_RELATIVE)
ARTIFACTS_DIRS_INSIDE_CONTAINER = {
    'logs': '/home/axonius/cortex/logs',
    'screenshots': '/home/axonius/cortex/screenshots'
}
AXONIUS_HOST_IMAGE_PATH = os.path.join(ROOT_DIR, 'libs', 'axonius-host-image')
DIR_MAP = {
    'integ': os.path.join('testing', 'tests'),
    'parallel': os.path.join('testing', 'parallel_tests'),
    'ui': os.path.join('testing', 'ui_tests', 'tests')
}
# The following line contains commands that we run before each new test. we are going to append more commands
# to it later, hence we have ./prepare_python_env.sh (for these commands)
FIRST_BASH_COMMANDS_BEFORE_EACH_TEST = 'set -e; source ./prepare_python_env.sh; ./clean_dockers.sh; '
MAX_SECONDS_FOR_ONE_JOB = 60 * 90  # no job (test / bunch of jobs) should take more than an hour an a half
MAX_SECONDS_FOR_THREAD_POOL = 60 * 120  # Just an extra caution for a timeout
AXONIUS_DNS_SERVER = 'dns.axonius.lan'
DOCKER_NETWORK_DEFAULT_GATEWAY = '172.17.0.1'
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
    def __init__(self, instance_memory):
        self.__docker = docker.from_env()
        self.__instances = self.__get_current_spawned_instances()
        self.storage_driver = self.__get_current_storage_driver()
        self.instance_memory = int(instance_memory * 0.9)   # usually a machine with x gb will report a little bit less
        print(f'Initialized Instance Manager. Currently spawned instances: {", ".join(self.__instances)}')
        print(f'Using storage driver: {self.storage_driver}')
        execute(f'rm -rf {ARTIFACTS_DIR_ABSOLUTE}')
        if not os.path.exists(ARTIFACTS_DIR_ABSOLUTE):
            os.makedirs(ARTIFACTS_DIR_ABSOLUTE)

    def __get_current_storage_driver(self):
        """
        Allows getting the current storage driver that docker uses, to allow mapping docker-in-docker using the same
        storage driver for faster results.
        :return:
        """
        storage_driver = self.__docker.info()['Driver'].strip()
        assert storage_driver != ''
        return storage_driver

    def __get_current_spawned_instances(self):
        return \
            {
                container.name.strip() for container in
                self.__docker.containers.list(
                    all=True,
                    filters={
                        'ancestor': AXONIUS_HOST_IMAGE_TAG,
                        'name': f'{AXONIUS_INSTANCES_PREFIX}*'
                    }
                )
            }

    def __get_current_irrelevant_instances(self):
        # Irrelevant instances are axonius instances which do not inherit from the most recent host image.
        return \
            {
                container.name.strip() for container in
                self.__docker.containers.list(
                    all=True,
                    filters={
                        'name': f'{AXONIUS_INSTANCES_PREFIX}*'
                    }
                )
            } - self.__get_current_spawned_instances()

    def __build_host_image(self):
        with TC.block('Building Host image..'):
            _, build_log = self.__docker.images.build(path=AXONIUS_HOST_IMAGE_PATH, tag=AXONIUS_HOST_IMAGE_TAG)
            for log in build_log:
                stream_message = log.get('stream')
                if stream_message:
                    print(stream_message.strip())

    def __spawn_instance(self, instance_number, image_tag):
        instance_name = f'{AXONIUS_INSTANCES_PREFIX}{instance_number}'
        https_port = int(f'{instance_number}443')
        db_port = int(f'{instance_number}270')

        # Remember! If you change these, you need to start your instance from scratch to allow the cached container
        # which always starts to reload!
        environment = dict()
        # Notice that we limit mongo to half of the memory instead 75%. we do this because tests do not run all adapters
        # and fetch everything at once, and we also do not have hundreds of thousands of devices, so this is unneeded.
        # but mongodb tends to catch everything it can so it reduces the effectiveness of other services.
        environment['MONGO_RAM_LIMIT_IN_GB'] = int(self.instance_memory * 0.5)
        environment['PUBLIC_HTTPS_PORT'] = https_port

        # Copy environment variables by teamcity.
        # Uncomment this if you need the inner containers to have specific environment variables, but do notice
        # that pytest acts differently when running under teamcity (outputs differently)
        #
        # for env_key, env_value in os.environ.items():
        #    if env_key.startswith('TEAMCITY') or env_key.startswith('BUILD'):
        #        environment[env_key] = env_value

        self.__docker.containers.run(
            image_tag,
            f'--storage-driver={self.storage_driver}',  # a param to the inner docker script
            name=instance_name,
            detach=True,
            privileged=True,
            ports={
                443: https_port,
                27017: db_port
            },
            volumes={
                '/dev/shm': {'bind': '/dev/shm', 'mode': 'rw'}
            },
            dns=[socket.gethostbyname(AXONIUS_DNS_SERVER)],  # bug in alpine needs only one dns
            mem_limit=f'{self.instance_memory}g',
            memswap_limit=f'{self.instance_memory * 3}g',
            mem_swappiness=90,
            oom_kill_disable=True,
            environment=environment
        )

        print(f'Spawning axonius instance {instance_name}, port mapping is ({https_port}, {db_port})')
        return instance_name

    def __shut_down_instance(self, instance_name):
        print(f'Shutting down {instance_name}..')
        self.__docker.containers.get(instance_name).remove(force=True, v=True)

    def __docker_execute(self, instance_name, job_name, commands, timeout=MAX_SECONDS_FOR_ONE_JOB, **kwargs):
        assert isinstance(commands, str), 'docker execute command must be a shell command'
        assert '"' not in commands, 'Not supported'
        commands = f'/bin/bash -c "{commands}"'  # disable temp | ts -s'  # ts to print timestamp
        if timeout > 0:
            commands = f'timeout -t {timeout} -s KILL {commands}'
        TC.print(f'{instance_name}: executing {job_name}: {commands}')
        start_time = time.time()
        rc, output = self.__docker.containers.get(instance_name).exec_run(['/bin/bash', '-c', commands], **kwargs)
        end_time = time.time()
        output = output.decode('utf-8')
        if rc != 0:
            if (end_time - start_time) > timeout:
                raise ValueError(f'Error, instance {instance_name} with job {job_name} and commands {commands} '
                                 f'timeout and was killed with SIGKILL. Output is {output}')
            else:
                raise ValueError(f'Error, instance {instance_name} with job {job_name} and '
                                 f'commands {commands} returned rc {rc}: {output}')

        return output

    def __execute_docker_on_all(self, job_name, command, max_parallel=None, **kwargs):
        """
        Executes a command, in parallel, on all containers.
        :param job_name: the job name
        :param command: the bash command to execute.
        :param max_parallel: The amount of parallel executions we can have, None for unlimited.
        :return:
        """
        what_to_run = [
            (
                self.__docker_execute,
                (instance_name, job_name, command),
                kwargs,
                instance_name
            ) for instance_name in self.__instances]
        yield from tp_execute(what_to_run, max_parallel or len(self.__instances))

    def __put_archive_in_all_dockers(self, tar_local_path, remote_path, **kwargs):
        """
        Copies a local path to a remote destination on all dockers.
        :param tar_local_path: the local path of a tar file
        :param remote_path: the remote path in which the tar file will be extracted
        :return:
        """

        def copy_tar_to_docker(instance_name, tar_location, docker_remote_path, **kwargs):
            with open(tar_location, 'rb') as f:
                return self.__docker.containers.get(instance_name).put_archive(docker_remote_path, f.read())

        what_to_run = [
            (
                copy_tar_to_docker,
                (instance_name, tar_local_path, remote_path),
                kwargs,
                instance_name
            ) for instance_name in self.__instances
        ]

        yield from tp_execute(what_to_run, len(self.__instances))

    def __get_archive_from_all_dockers(self, remote_path, **kwargs):
        """
        Copies a remote path to local_path/container_name
        :param remote_path: the remote path to be returned as a tar archive
        :return:
        """

        def get_tar_from_docker(instance_name, docker_remote_path, **kwargs):
            return self.__docker.containers.get(instance_name).get_archive(docker_remote_path)

        what_to_run = [
            (
                get_tar_from_docker,
                (instance_name, remote_path),
                kwargs,
                instance_name
            ) for instance_name in self.__instances
        ]

        yield from tp_execute(what_to_run, len(self.__instances))

    def spawn_axonius_instances(self, number_of_instances: int, do_not_use_cache: bool):
        """
        Creates {number_of_instances} independent containers with as much requirements already built and ready on them.
        :param number_of_instances: the number of instances to spawn
        :param bool do_not_use_cache: whether or not we should use caching for building axonius.
        :return:
        """
        # Build the host image. In case it changed, it means that the current instances we think we have
        # also changed, since they inherit from an old image. In that case we have to remove them.
        self.__build_host_image()
        self.__instances = self.__get_current_spawned_instances()
        irrelevant_instances = self.__get_current_irrelevant_instances()
        if irrelevant_instances:
            print('Some instances on this host are out-dated since they are using an old host image. '
                  'Shutting them down')
            for instance_name in irrelevant_instances:
                self.__shut_down_instance(instance_name)

        # We should have all instances or none of them. If that is not the case then shut down whatever we have
        # and restart all. Also, if the user does not want any caching lets shut down everything
        if len(self.__instances) != number_of_instances or do_not_use_cache:
            for instance_name in self.__instances:
                self.__shut_down_instance(instance_name)

            for i in range(1, number_of_instances + 1):
                self.__spawn_instance(i, AXONIUS_HOST_IMAGE_TAG)

            self.__instances = self.__get_current_spawned_instances()
            assert len(self.__instances) == number_of_instances

        # Docker has a bug (https://github.com/docker/for-linux/issues/506), if we commit a container which has
        # containers in it, we will not see these containers in the new docker. So we will have to build Axonius
        # on all containers instead of building on one and duplicating it.
        # Do notice that we do that using caching so the next time they are built it will be very fast.

        # At this point we have a list of new/cached instance. We have to copy the new source code.
        # 1. We try to cache venv. If the user does not want any caching then the container is new anyway so this will
        # silently fail, since this is a legitimate scenario (on first run, venv isn't there).
        # We also delete the old source code
        list(self.__execute_docker_on_all('Remove tmp venv', 'rm -rf /tmp/venv'))
        list(self.__execute_docker_on_all('Move venv to tmp location',
                                          'mv /home/axonius/cortex/venv /tmp/venv; exit 0'))    # silently fail
        list(self.__execute_docker_on_all('Delete /home/axonius', 'rm -rf /home/axonius/*'))
        list(self.__execute_docker_on_all('Mkdir cortex', 'mkdir /home/axonius/cortex'))
        for instance_name, ret, overall_time in self.__execute_docker_on_all('show files on axonius',
                                                                             'ls -lahR /home/axonius'):
            with TC.block(f'content of {instance_name}:/home/axonius'):
                print(ret)

        # 2. Create a copy of the source code and copy it to there.
        # Note that using 'docker cp' is way slower (more than a minute vs 5-10 sec)
        print(f'Creating source code tar and copying it..')
        execute('shopt -s dotglob; tar cf cortex.tar '
                '--exclude venv --exclude __pycache__ '
                f'--exclude .idea --exclude logs --exclude .cache *')

        list(self.__put_archive_in_all_dockers('cortex.tar', '/home/axonius/cortex'))
        list(self.__execute_docker_on_all('Restore venv from tmp to cortex',
                                          'mv /tmp/venv /home/axonius/cortex/venv; exit 0'))    # fail silently

        # 3. Clean running containers and volumes beforehand and install axonius
        for instance_name, ret, overall_time in self.__execute_docker_on_all('Clean dockers',
                                                                             'cd cortex; ./clean_dockers.sh'):
            with TC.block(f'Finished cleaning instance {instance_name}, took {overall_time} seconds'):
                print(ret)

        print(f'Source code copying complete, installing Axonius..')
        execute('rm cortex.tar')
        # We build everything. Notice that if we have more than X machines we prefer building with thread-pools of X
        # since building Axonius is a relatively very consuming event (for most cases, more than testing)
        for instance_name, ret, overall_time in \
                self.__execute_docker_on_all('Prepare ci env with caching of images',
                                             'cd cortex; ./prepare_ci_env.sh --cache-images',
                                             max_parallel=MAX_PARALLEL_PREPARE_CI_ENV_JOBS):
            with TC.block(f'Finished building axonius on {instance_name}, took {overall_time} seconds'):
                print(ret)

    def spawn_selenium_instances(self, number_of_instances: int):
        """
        Creates {number_of_instances} independent containers with as much requirements already built and ready on them.
        :param number_of_instances: the number of instances to spawn
        :return:
        """

        # Since this is so fast to create we will just shut down whatever we have on now
        for container in self.__docker.containers.list(
                all=True,
                filters={
                    'name': f'{SELENIUM_INSTANCE_PREFIX}*'
                }
        ):
            print(f'Killing container {container.name.strip()}')
            container.remove(force=True, v=True)    # Force removal + remove volume

        # Lets pull the newest version, to test on the latest grid + latest chrome.
        print(f'Downloading new versions of selenium')
        self.__docker.images.pull('selenium/hub', 'latest')
        self.__docker.images.pull('selenium/node-chrome', 'latest')

        selenium_hub_container_name = f'{SELENIUM_INSTANCE_PREFIX}hub'
        print(f'Raising hub {selenium_hub_container_name}')
        self.__docker.containers.run(
            'selenium/hub',
            name=selenium_hub_container_name,
            detach=True,
            ports={
                4444: 4444
            },
            volumes={
                '/dev/shm': {'bind': '/dev/shm', 'mode': 'rw'}
            },
            environment={
                'TZ': 'Asia/Jerusalem'
            }
        )

        for i in range(number_of_instances):
            selenium_node_container_name = f'{SELENIUM_INSTANCE_PREFIX}chrome-{i}'
            print(f'Raising node {selenium_node_container_name}')
            self.__docker.containers.run(
                'selenium/node-chrome',
                name=selenium_node_container_name,
                detach=True,
                volumes={
                    '/dev/shm': {'bind': '/dev/shm', 'mode': 'rw'}
                },
                links={
                    selenium_hub_container_name: 'hub'
                },
                ports={
                    5900: (5900 + i + 1)    # VNC Port
                },
                environment={
                    'TZ': 'Asia/Jerusalem'
                },
                extra_hosts={
                    'okta.axonius.local': DOCKER_NETWORK_DEFAULT_GATEWAY
                }
            )

    def prepare_host_machine(self, do_not_use_cache):
        # self.instance_memory is the amount of memory we give to each instance. In addition we give 4gb for grid
        # and 2gb for each container for its chrome instance.
        current_machine_ram_in_gb = int(psutil.virtual_memory().total / (1024 ** 3))
        if current_machine_ram_in_gb < self.instance_memory:
            print(f'Warning: Axonius requires at least {self.instance_memory}gb ram, '
                  f'but this machine has {current_machine_ram_in_gb}gb.')
            # This is to allow people to run tests on their own machine which is usually weaker.
            number_of_instances = 1
        else:
            number_of_instances = int(
                (current_machine_ram_in_gb - GB_NEEDED_FOR_GRID) /
                (self.instance_memory + GB_NEEDED_FOR_CHROME_INSTANCE)
            )

        print(f'Spawning {number_of_instances} Selenium instances '
              f'with {"no caching" if do_not_use_cache else "caching"}')

        self.spawn_selenium_instances(number_of_instances)

        print(f'Spawning {number_of_instances} Axonius instances '
              f'with {"no caching" if do_not_use_cache else "caching"}')

        self.spawn_axonius_instances(number_of_instances, do_not_use_cache)

        print(f'Done preparing host machine')

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

        def docker_execute_on_next_free_instance(command_job_name, command):
            # Do note this function runs in different threads and thus should be thread-safe in terms of printing.
            # We use the flow-id feature of teamcity to achieve this.
            start_time = time.time()
            with free_instances_lock:
                instance_to_run_on = free_instances.pop()

            try:
                current_output = self.__docker_execute(instance_to_run_on, command_job_name,
                                                       command)
            except Exception as e:
                current_output = e

            current_docker_logs = self.__docker.containers.get(instance_to_run_on).logs().decode('utf-8')

            # Create the test artifacts folder
            if not os.path.exists(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name)):
                os.makedirs(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name))

            if not os.path.exists(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name, 'xml')):
                os.makedirs(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name, 'xml'))

            # Start putting artifacts in this folder
            current_logs_tar_file_name = f'{command_job_name}_logs.tar'
            logs_tar_file_location = os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name, current_logs_tar_file_name)
            with open(logs_tar_file_location, 'wb') as tar_file_obj:
                for chunk in self.__docker.containers.get(instance_to_run_on).get_archive(
                        ARTIFACTS_DIRS_INSIDE_CONTAINER['logs'])[0]:
                    tar_file_obj.write(chunk)

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

            # Try getting screenshots. If we are in parallel tests this might fail
            try:
                screenshots_tar_file = b''
                for chunk in self.__docker.containers.get(instance_to_run_on).get_archive(
                        ARTIFACTS_DIRS_INSIDE_CONTAINER['screenshots'])[0]:
                    screenshots_tar_file += chunk

                # Also all the screenshots
                with tarfile.open(fileobj=io.BytesIO(screenshots_tar_file)) as tar_file:
                    tar_file.extractall(os.path.join(ARTIFACTS_DIR_ABSOLUTE, command_job_name))
            except docker.errors.NotFound:
                # This is legitimate, we do not always have screenshots.
                pass

            with free_instances_lock:
                free_instances.add(instance_to_run_on)

            return instance_to_run_on, current_output, current_docker_logs, time.time() - start_time

        for (job_name, ret, total_time_including_waiting_and_getting_artifacts) in tp_execute(
                [
                    (
                        docker_execute_on_next_free_instance,
                        (job_name, job_val, ),
                        {},
                        job_name
                    ) for job_name, job_val in jobs.items()
                ],
                len(free_instances)
        ):
            ret_instance_name, output, docker_logs, overall_time = ret
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
                with TC.block('docker logs'):
                    print(docker_logs)
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

        print(f'Finished with all tests, below are all tests with the time they took, ordered by the time of run')
        for i, message in enumerate(tests_statistics):
            print(f'{i}. {message}')

        # If there was at least one exception we should exit.
        if len(tests_with_exceptions) > 0:
            # An exception in the code should fail the script, otherwise the test could pass.
            # Note that this is something that should bearly happen (it indicates problems in the CI, not in the
            # tests)
            sys.stderr.write(f'The following exceptions happened: {tests_with_exceptions}')
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
    test prepare all -d -> prepares the environment needed for this type of tests.
    test run all -> runs all tests on this host.
    test run all -d -> runs all tests on this host, distributed. This will run as much Axonius system as possible on 
                        this host.
    test run parallel -p test_aws.py::test_fetch_devices -> runs this specific test.
    test run ut -p axonius-libs/tests/test_async.py -> runs this specific module.
    test run ui -p test_bad_login.py -> runs this specific module.
    ''')
    parser.add_argument('action', choices=['run', 'prepare'])
    parser.add_argument('target', choices=['all', 'ut', 'integ', 'parallel', 'ui'], help='Which scenario to run')
    parser.add_argument('-p', '--path', help='In case of running a specific test, this would be the path')
    parser.add_argument('-d', '--distributed', action='store_true',
                        help='Distributed run, this will run a couple of Axonius systems on this host')
    parser.add_argument('--no-cache', type=str, default='false', help='Do not cache, rebuild axonius from scratch.')
    parser.add_argument('--instance-memory', type=int, default=DEFAULT_AXONIUS_INSTANCE_RAM_IN_GB,
                        help='Set memory for each distributed instance. This should be used only for debugging')
    parser.add_argument('--max-parallel-builder-tasks', type=int, default=DEFAULT_MAX_PARALLEL_TESTS_IN_INSTANCE,
                        help='Set the amount of max jobs in the parallel builder (which can be run distributed). '
                             'This should be used only for debugging')

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    no_cache = args.no_cache.lower() == 'true'
    print(f'Distributed mode: {args.distributed}')
    print(f'No Cache: {no_cache}')
    print(f'Instance Memory: {args.instance_memory}')
    print(f'Max Parallel Builder Tasks: {args.max_parallel_builder_tasks}')

    if args.action == 'prepare':
        if args.distributed:
            instance_manager = InstanceManager(args.instance_memory)
            instance_manager.prepare_host_machine(no_cache)
        else:
            with TC.block(f'Preparing this host. Building Axonius'):
                child = subprocess.Popen(
                    f'/usr/bin/env bash -c "source ./prepare_python_env.sh; ./prepare_ci_env.sh"',
                    shell=True
                )
                child.communicate()
                if child.returncode != 0:
                    raise ValueError(f'Error, building Axonius returned rc {child.returncode}')

    if args.action == 'run':
        print(f'Is running under teamcity: {TC.is_in_teamcity()}')

        def get_ut_tests_jobs():
            return {
                'Unit Tests': './run_ut_tests.sh'
            }

        def get_integ_tests_jobs():
            integ_tests = get_list_of_tests_in_path(os.path.join(ROOT_DIR, DIR_MAP['integ']))
            with TC.block('Collected integration tests modules'):
                for test_module in integ_tests:
                    print(test_module)

            return {
                'integ_' + file_name.split('.py')[0]:
                    f'python3 -u ./testing/run_pytest.py {os.path.join(DIR_MAP["integ"], file_name)}'
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

                parallel_jobs[job_name] = f'python3 -u ./testing/run_parallel_tests.py {files_list}'

            return parallel_jobs

        def get_ui_tests_jobs():
            ui_tests = get_list_of_tests_in_path(os.path.join(ROOT_DIR, DIR_MAP['ui']))
            with TC.block('Collected ui tests modules'):
                for test_module in ui_tests:
                    print(test_module)

            return {
                'ui_' + test_module.split('.py')[0]:
                    f'python3 -u ./testing/run_ui_tests.py --host-hub {os.path.join(DIR_MAP["ui"], test_module)}'
                for test_module in ui_tests
            }

        jobs = dict()
        # Collect jobs
        if args.target in ['ut', 'all']:
            jobs.update(get_ut_tests_jobs())
        if args.target in ['integ', 'all']:
            jobs.update(get_integ_tests_jobs())
        if args.target in ['parallel', 'all']:
            jobs.update(get_parallel_tests_jobs())
        if args.target in ['ui', 'all']:
            jobs.update(get_ui_tests_jobs())

        with TC.block(f'Jobs for target {args.target}'):
            for job_name, job_value in jobs.items():
                print(f'{job_name}: {job_value}')

        bash_commands_before_each_test = FIRST_BASH_COMMANDS_BEFORE_EACH_TEST
        for artifact_dir in ARTIFACTS_DIRS_INSIDE_CONTAINER.values():
            bash_commands_before_each_test += 'rm -rf ' + os.path.join(artifact_dir, '*') + '; '
        if args.distributed:
            print(f'Running on distributed mode')
            instance_manager = InstanceManager(args.instance_memory)
            for job_name in jobs:
                jobs[job_name] = f'cd cortex; {bash_commands_before_each_test} {jobs[job_name]}'
            instance_manager.execute_jobs(jobs)
        else:
            print(f'Running on this host')
            for job_name, job_cmd in jobs.items():
                job_cmd = f'/usr/bin/env bash -c "{bash_commands_before_each_test} {job_cmd}"'
                print(f'job {job_name}: {job_cmd}')
                child = subprocess.Popen(job_cmd, shell=True)
                child.communicate()
                if child.returncode != 0:
                    raise ValueError(f'Error, job {job_name}: {job_cmd} returned rc {child.returncode}')


if __name__ == '__main__':
    sys.exit(main())
