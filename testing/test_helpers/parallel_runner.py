import time
import subprocess
import os

try:
    from axonius.utils.debug import COLOR
except ModuleNotFoundError:
    COLOR = {}


class ParallelRunner(object):
    def __init__(self):
        self.wait_list = {}
        self.start_times = {}
        self.logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'build_log'))
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

    def std_file(self, task_name):
        return os.path.join(f"{self.logs_dir}", f"task_{task_name}_std.log")

    def err_file(self, task_name):
        return os.path.join(f"{self.logs_dir}", f"task_{task_name}_err.log")

    def append_single(self, task_name, args, **kwargs):
        command = ' '.join(args)
        print(f"Running {COLOR.get('light_blue', '<')}{command}{COLOR.get('reset', '>')}")
        stdout = open(self.std_file(task_name), "wb")
        stderr = open(self.err_file(task_name), "wb")
        process = subprocess.Popen(args, stdout=stdout, stderr=stderr, **kwargs)
        self.wait_list[task_name] = process
        self.start_times[task_name] = time.time()
        return process

    def wait_for_all(self, timeout=45 * 60):
        ret_code = 0
        start = time.time()
        first = True
        try:
            while start + timeout > time.time():
                for name, proc in self.wait_list.copy().items():
                    status = "Finished"
                    if proc.poll() is not None:
                        if proc.returncode != 0:
                            print(f'{name} failed')
                            status = "Failed"
                            self.pump_std(name, proc)
                            if proc.returncode != 0:
                                ret_code = proc.returncode

                        seconds = int(time.time() - self.start_times[name])
                        del self.wait_list[name]
                        del self.start_times[name]

                        or_less = ' or less' if first else ''

                        print(f"{status} {name} in {seconds} seconds{or_less}. Still waiting for {list(self.wait_list.keys())}")

                if bool(self.wait_list):
                    time.sleep(0.5)
                    first = False
                else:
                    break

            if len(self.wait_list) > 0:
                for proc in self.wait_list:
                    print(f"{proc} timed out")
                raise Exception("Not all tasks finished successfully")
            return ret_code
        finally:
            self.clean()

    def pump_std(self, name, proc):
        print(name, f"{COLOR.get('light_magenta', '')}STDOUT{COLOR.get('reset', '')}")
        print(open(self.std_file(name), "rb").read().decode("utf-8"))
        error = open(self.err_file(name), "rb").read().decode("utf-8")
        if error.strip():
            print(name, f"{COLOR.get('light_red', '')}STDERR{COLOR.get('reset', '')}")
            print(error)

    def __del__(self):
        self.clean()

    def clean(self):
        for procname in self.wait_list.keys():
            print(f"Killing timed out process {procname}")
            self.try_kill(procname)

    def try_kill(self, procname):
        try:
            proc = self.wait_list[procname]
            proc.kill()
            self.pump_std(procname, proc)
        except Exception as e:
            print(e)
