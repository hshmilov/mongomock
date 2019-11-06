import sys
import time
import subprocess
import os

try:
    from axonius.utils.debug import COLOR
except ModuleNotFoundError:
    COLOR = {}

MAX_PARALLEL_TASKS = 10
SUBPROCESS_POLLING_INTERVAL_IN_SEC = 5
MAX_RETRIES = 3


class ParallelRunner(object):
    def __init__(self):
        self.waiting_list = []
        self.running_list = {}
        self.start_times = {}
        self.all_tasks = {}
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

        process = subprocess.Popen(args, **kwargs)
        self.running_list[task_name] = process
        self.start_times[task_name] = time.time()
        self.all_tasks[task_name]['running_count'] += 1
        return process

    def append_single(self, task_name, args, **kwargs):
        self.waiting_list.append((task_name, args, kwargs))
        if task_name not in self.all_tasks:
            self.all_tasks[task_name] = {
                'name': task_name,
                'args': args,
                'kwargs': kwargs,
                'running_count': 0
            }
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
            failed_tasks = dict()
            while start + timeout > time.time():
                for name, proc in self.running_list.copy().items():
                    status = "Finished"
                    if proc.poll() is not None:
                        seconds = int(time.time() - self.start_times[name])
                        del self.running_list[name]
                        del self.start_times[name]
                        ret_code = proc.returncode
                        if proc.returncode != 0:
                            task = self.all_tasks[name]
                            run_count = task['running_count']
                            sys.stderr.write(f'{name} failed, code {proc.returncode}, try: {run_count}\n')
                            sys.stderr.flush()
                            status = "Failed"
                            if run_count < MAX_RETRIES:
                                self.append_single(task['name'], task['args'], **task['kwargs'])
                            else:
                                failed_tasks[name] = proc.returncode

                        or_less = ' or less' if first else ''

                        print(
                            f"{status} {name} in {seconds} seconds{or_less}. Still waiting for "
                            f"{list(self.running_list.keys())}")

                        # Put a new process to run
                        if len(self.waiting_list) > 0:
                            self.__run_next_task()
                if (len(self.running_list) + len(self.waiting_list)) > 0:
                    time.sleep(SUBPROCESS_POLLING_INTERVAL_IN_SEC)
                    first = False
                else:
                    break

            if self.running_list or failed_tasks:
                for proc in self.running_list:
                    sys.stderr.write(f"{proc} timed out\n")
                for future_task in self.waiting_list:
                    sys.stderr.write(f"{future_task[0]} did not start running because of the timeout\n")
                for failed_task_name, failed_task_rc in failed_tasks.items():
                    sys.stderr.write(f'{failed_task_name} failed with return code {failed_task_rc}\n')
                sys.stderr.flush()
                raise Exception("Not all tasks finished successfully")
            return ret_code
        finally:
            self.clean()

    def __del__(self):
        self.clean()

    def clean(self):
        for procname in self.running_list:
            sys.stdout.write(f"Killing timed out process {procname}\n")
            sys.stdout.flush()
            self.try_kill(procname)

    def try_kill(self, procname):
        try:
            proc = self.running_list[procname]
            proc.kill()
        except Exception as e:
            sys.stderr.write(f'Exception while killing {procname}: {str(e)}\n')
            sys.stderr.flush()
