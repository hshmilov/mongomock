import time
import glob
import subprocess
import os
import sys


class ParallelRunner(object):
    def __init__(self):
        self.wait_list = {}
        self.start_times = {}

    def append_pattern(self, pattern, tag_prefix):
        for some_dir in glob.glob(pattern):
            adapter_name = os.path.basename(some_dir)
            command = "docker build ../{1}/{0} -t axonius/{0}".format(adapter_name, tag_prefix)
            self.append_single(adapter_name, command)

    def append_single(self, task_name, command):
        print(f"Running <{command}>")
        self.wait_list[task_name] = subprocess.Popen(
            command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.start_times[task_name] = time.time()

    def wait_for_all(self):
        try:
            for _ in range(0, 500):
                for name, proc in self.wait_list.copy().items():
                    if proc.poll() is not None:
                        if proc.returncode != 0:
                            print(f'Failed to build {name}')
                            self.pump_std(name, proc)
                        else:
                            seconds = int(time.time() - self.start_times[name])
                            print(f"Finished building {name} in {seconds} seconds")

                        del self.wait_list[name]
                        del self.start_times[name]

                if bool(self.wait_list):
                    time.sleep(5)
                else:
                    break

            if len(self.wait_list) > 0:
                for proc in self.wait_list:
                    print(f"{proc} timed out")
                raise Exception("Not all containers were built")
        finally:
            self.clean()

    def pump_std(self, name, proc):
        print(name, "STDOUT")
        print(proc.stdout.read().decode("utf-8"))
        print(name, "STDERR")
        print(proc.stderr.read().decode("utf-8"))

    def __del__(self):
        self.clean()

    def clean(self):
        for procname in self.wait_list.keys():
            print("Killing timed out process")
            self.try_kill(procname)

    def try_kill(self, procname):
        try:
            proc = self.wait_list[procname]
            proc.kill()
            self.pump_std(procname, proc)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    os.chdir(os.path.dirname(sys.argv[0]))

    runner = ParallelRunner()

    # first build libs
    runner.append_single("axonius-libs", "docker build ../plugins/axonius-libs -t axonius/axonius-libs")
    print("waiting to build axonius-libs")
    runner.wait_for_all()

    # venv
    runner.append_single("venv", "../create_venv.sh")

    # badly named plugins :(
    runner.append_single("core", "docker build ../plugins/core -t axonius/core")
    runner.append_single("gui", "docker build ../plugins/gui -t axonius/gui")
    runner.append_single("watch-service", "docker build ../plugins/watch-service -t axonius/watch-service")

    # plugins
    runner.append_single("aggregator", "docker build ../plugins/aggregator-plugin -t axonius/aggregator")

    # adapters
    runner.append_pattern('../adapters/*-adapter', 'adapters')

    runner.wait_for_all()
