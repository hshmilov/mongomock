import time
import subprocess
import os

try:
    from axonius.utils.debug import COLOR
except ModuleNotFoundError:
    COLOR = {}

MAX_PARALLEL_TASKS = 10
SUBPROCESS_POLLING_INTERVAL_IN_SEC = 5


class ParallelRunner(object):
    def __init__(self):
        self.waiting_list = []
        self.running_list = {}
        self.start_times = {}
        self.logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'build_log'))
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

    def err_file(self, task_name):
        return os.path.join(f"{self.logs_dir}", f"task_{task_name}_err.log")

    def __run_next_task(self):
        # Actually executes the task
        task_name, args, kwargs = self.waiting_list.pop(0)
        command = ' '.join(args)
        print(f"[{len(self.running_list) + 1} / {MAX_PARALLEL_TASKS}] "
              f"Running {COLOR.get('light_blue', '<')}{command}{COLOR.get('reset', '>')}")
        stderr = kwargs.pop('stderr', None)
        stderr = stderr if stderr is not None else open(self.err_file(task_name), "wb")

        process = subprocess.Popen(args, stderr=stderr, **kwargs)
        self.running_list[task_name] = process
        self.start_times[task_name] = time.time()
        return process

    def append_single(self, task_name, args, **kwargs):
        self.waiting_list.append((task_name, args, kwargs))
        # runs the task or adds it to the waiting list to be run afterwards.
        if len(self.running_list) < MAX_PARALLEL_TASKS:
            self.__run_next_task()
            return True

        return False

    def wait_for_all(self, timeout=90 * 60):
        ret_code = 0
        start = time.time()
        first = True
        try:
            while start + timeout > time.time():
                for name, proc in self.running_list.copy().items():
                    status = "Finished"
                    if proc.poll() is not None:
                        if proc.returncode != 0:
                            print(f'{name} failed')
                            status = "Failed"
                            self.pump_std(name, proc)
                            if proc.returncode != 0:
                                ret_code = proc.returncode

                        seconds = int(time.time() - self.start_times[name])
                        del self.running_list[name]
                        del self.start_times[name]

                        or_less = ' or less' if first else ''

                        print(
                            f"{status} {name} in {seconds} seconds{or_less}. Still waiting for {list(self.running_list.keys())}")

                        # Put a new process to run
                        if len(self.waiting_list) > 0:
                            self.__run_next_task()

                if (len(self.running_list) + len(self.waiting_list)) > 0:
                    time.sleep(SUBPROCESS_POLLING_INTERVAL_IN_SEC)
                    first = False
                else:
                    break

            if len(self.running_list) > 0:
                for proc in self.running_list:
                    print(f"{proc} timed out")
                for future_task in self.waiting_list:
                    print(f"{future_task[0]} did not start running because of the timeout")
                raise Exception("Not all tasks finished successfully")
            return ret_code
        finally:
            self.clean()

    def pump_std(self, name, proc):
        print(name, f"{COLOR.get('light_magenta', '')}STDOUT{COLOR.get('reset', '')}")
        error = open(self.err_file(name), "rb").read().decode("utf-8")
        if error.strip():
            print(name, f"{COLOR.get('light_red', '')}STDERR{COLOR.get('reset', '')}")
            print(error)

    def __del__(self):
        self.clean()

    def clean(self):
        for procname in self.running_list.keys():
            print(f"Killing timed out process {procname}")
            self.try_kill(procname)

    def try_kill(self, procname):
        try:
            proc = self.running_list[procname]
            proc.kill()
            self.pump_std(procname, proc)
        except Exception as e:
            print(e)
