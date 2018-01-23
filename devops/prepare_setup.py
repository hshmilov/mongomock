import glob
import os
import sys
from parallel_runner import ParallelRunner
import time


class ParallelDockerBuilder(ParallelRunner):

    def append_docker_pattern(self, pattern, tag_prefix, **kwargs):
        for some_dir in glob.glob(pattern):
            container_name = os.path.basename(some_dir)
            time.sleep(3)  # We are getting resource busy. I suspect this is due parallel build storm
            command = "docker build ../{1}/{0} -t axonius/{0}".format(container_name, tag_prefix)
            self.append_single(container_name, command, **kwargs)


if __name__ == '__main__':
    os.chdir(os.path.dirname(sys.argv[0]))

    runner = ParallelDockerBuilder()

    # first build libs
    runner.append_single("axonius-libs", "docker build ../plugins/axonius-libs -t axonius/axonius-libs")
    print("waiting to build axonius-libs")
    assert runner.wait_for_all() == 0

    # venv
    runner.append_single("venv", "../create_venv.sh")

    # badly named plugins :(
    runner.append_single("core", "docker build ../plugins/core -t axonius/core")
    runner.append_single("gui", "docker build ../plugins/gui -t axonius/gui")
    runner.append_single("watch-service", "docker build ../plugins/watch-service -t axonius/watch-service")

    # plugins
    runner.append_docker_pattern('../plugins/*-plugin', 'plugins')

    # adapters
    runner.append_docker_pattern('../adapters/*-adapter', 'adapters')

    assert runner.wait_for_all() == 0
