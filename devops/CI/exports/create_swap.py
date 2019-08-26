import os
import shutil
from pathlib import Path
import subprocess
import shlex

SWAPFILE_LOCATION = Path('/swapfile')
BYTES_TO_GB = 1024 * 1024 * 1024


def run(cmd):
    print(f'running {cmd}')
    return subprocess.check_output(shlex.split(cmd))


def create_swap(filename, size_gb):
    run(f'/usr/bin/fallocate -l {size_gb}G {filename}')
    run(f'/bin/chmod 0600 {filename}')
    run(f'/sbin/mkswap {filename}')
    run(f'/sbin/swapon {filename}')

    fstab = Path('/etc/fstab')
    content = fstab.read_text()
    content += f'\n{filename} none swap sw 0 0\n'
    fstab.write_text(content)


def main():
    try:
        if SWAPFILE_LOCATION.is_file():
            SWAPFILE_LOCATION.unlink()
    except Exception:
        print('Swap exists and in use. Skipping ...')
        return

    free_space_gb = shutil.disk_usage('/').free / BYTES_TO_GB
    mem_gb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / BYTES_TO_GB
    desired_swap_size = max(int(mem_gb * 2 + 1), 64)  # swap should be more or less twice the size of RAM

    if free_space_gb > desired_swap_size * 1.2:  # lets have some 20% spare disk size
        create_swap(SWAPFILE_LOCATION, desired_swap_size)
    else:
        print(f'Not creating swap, not enough free space: {free_space_gb}. needed: {desired_swap_size}')


if __name__ == '__main__':
    main()
