import crypt
from pathlib import Path
import subprocess
import secrets
import time
import uptime

from scripts.watchdog.watchdog_task import WatchdogTask

UBUNTU_USER = 'ubuntu'
DEFAULT_UBUNTU_PASS = 'bringorder'
SLEEP_TIME = 60 * 5
UPTIME_THRESH = 24 * 60 * 60


class ResetPasswordsTask(WatchdogTask):
    def __init__(self):
        super().__init__(name=self.__class__.__name__.lower())

    def run(self):

        while True:
            self.report_info(f'{self.name} is running')
            time.sleep(SLEEP_TIME)

            if uptime.uptime() < UPTIME_THRESH:
                self.report_info('Uptime is lower than the thresh to change password')
                continue

            user = UBUNTU_USER
            new_passw = secrets.token_hex(32)
            try:
                lines = Path('/etc/shadow').read_text().split()
                for _user, _hash in [(line.split(':')[0], line.split(':')[1]) for line in lines]:
                    if user != _user:
                        continue  # forward until we reach the correct user
                    if _hash == crypt.crypt(DEFAULT_UBUNTU_PASS, _hash):
                        self.report_info(f'changing password')
                        p = subprocess.Popen(['/usr/sbin/chpasswd'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                        out, err = p.communicate(f'{user}:{new_passw}\n'.encode())
                        ret = p.wait(60)
                        if ret == 0:
                            self.report_info(f'password changed - {ret} {out} {err}. Exiting.')
                            return
                        else:
                            self.report_error(f'failed to change password (will retry)! {ret} {out} {err}')
                    else:
                        self.report_info(f'password was not default, doing nothing')
                        return
            except Exception as e:
                self.report_error(f'failure to change password {e}')


if __name__ == '__main__':
    gw = ResetPasswordsTask()
    gw.start()
