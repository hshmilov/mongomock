"""
This script is intended to get all the external libraries we have in the system, their version, and their license.
The output is a report of these.

The list of everything we have:
Python:
* python3 reqs (requirements.txt)
* python2 reqs (requirements2.txt)
* standalone packages (exceptional packages which are not listed)

VueJS:
* package.json

Binaries:
* init_host.sh
* Dockerfile

"""
import os
import sys
import subprocess
import glob

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def execute(commands, cwd=None):
    shell = False if isinstance(commands, list) else True
    proc = subprocess.Popen(commands, shell=shell, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    assert proc.returncode == 0 and stderr == '', \
        f'Error for for {commands}:\nReturn Code: {proc.returncode}\nStderr:\n{stderr}Stdout:\n{stdout}'

    return stdout


def get_final_req_file(pattern):
    packages = []
    packages_with_version = []
    for file_path in glob.iglob(pattern, recursive=True):
        with open(file_path, 'rt') as f:
            for req in f.readlines():
                req = req.strip().lower()
                if req:
                    req_name = req.split('==')[0]
                    if req_name in packages and req not in packages_with_version:
                        raise ValueError(f'Error! package {req_name} appears twice with different versions')
                    packages.append(req_name)
                    packages_with_version.append(req)

    return packages_with_version


def main():
    print(f'[+] Collecting python3 packages...')
    all_python3_reqs = get_final_req_file(os.path.join(ROOT_DIR, '**', 'requirements.txt'))
    print(f'[+] Collecting python2 packages...')
    all_python2_reqs = get_final_req_file(os.path.join(ROOT_DIR, '**', 'requirements2.txt'))

    print(f'[+] Writing final requirements files')
    with open(f'reqs_final.txt', 'wt') as f:
        f.write('\n'.join(all_python3_reqs))

    with open(f'reqs_final2.txt', 'wt') as f:
        f.write('\n'.join(all_python2_reqs))


if __name__ == '__main__':
    sys.exit(main())
