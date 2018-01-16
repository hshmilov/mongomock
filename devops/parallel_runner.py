import time
import subprocess
import os


class ParallelRunner(object):
    def __init__(self):
        self.wait_list = {}
        self.start_times = {}
        self.logs_dir = "../logs/build_log/"
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

    def std_file(self, task_name):
        return f"{self.logs_dir}task_{task_name}_std.log"

    def err_file(self, task_name):
        return f"{self.logs_dir}task_{task_name}_err.log"

    def append_single(self, task_name, command, **kwargs):
        print(f"Running <{command}>")
        stdout = open(self.std_file(task_name), "wb")
        stderr = open(self.err_file(task_name), "wb")
        self.wait_list[task_name] = subprocess.Popen(command.split(), stdout=stdout, stderr=stderr, **kwargs)
        self.start_times[task_name] = time.time()

    def wait_for_all(self, times=500, sleep_period=5):
        ret_code = 0
        try:
            for _ in range(0, times):
                for name, proc in self.wait_list.copy().items():
                    status = "Finished"
                    if proc.poll() is not None:
                        if proc.returncode != 0:
                            print(f'{name} failed')
                            status = "Failed"
                            self.pump_std(name, proc)
                            ret_code = proc.returncode

                        seconds = int(time.time() - self.start_times[name])
                        del self.wait_list[name]
                        del self.start_times[name]

                        print(f"{status} {name} in {seconds} seconds. Still waiting for {list(self.wait_list.keys())}")

                if bool(self.wait_list):
                    time.sleep(sleep_period)
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
        print(name, "STDOUT")
        print(open(self.std_file(name), "rb").read().decode("utf-8"))
        print(name, "STDERR")
        print(open(self.err_file(name), "rb").read().decode("utf-8"))

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
