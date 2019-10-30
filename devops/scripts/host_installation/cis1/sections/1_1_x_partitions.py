from plumbum.cmd import mount, grep, echo, sudo, tee
from plumbum import colors

# cis section 1.1.{3,4,7,8,9,14,15,16,17,18,19}

TMP_MOUNT = '/tmp'
VAR_TMP_MOUNT = '/var/tmp'
DEV_SHM_MOUNT = '/dev/shm'
CDROM = 'cdrom'
FLOPPY = 'floppy'

NODEV = 'nodev'
NOSUID = 'nosuid'
NOEXEC = 'noexec'


def have_flag_in_mount(mnt, flag):
    ch = mount | grep[mnt] | grep[flag]
    return ch.run(retcode=None)[0] == 0


def check_tmp():
    flags_ok = have_flag_in_mount(TMP_MOUNT, NODEV) and have_flag_in_mount(TMP_MOUNT, NOSUID)
    if not flags_ok:
        print(colors.yellow | f'missing flags in {TMP_MOUNT} mount')
        (echo[f'tmpfs {TMP_MOUNT} tmpfs rw,nosuid,nodev'] | tee['-a', '/etc/fstab'])()
        print(colors.yellow | f'fstab was modified. please reboot so the change will take an effect')
    else:
        print(colors.green | f'{TMP_MOUNT} is ok')


def check_var_tmp():
    mnt = VAR_TMP_MOUNT
    flags_ok = have_flag_in_mount(mnt, NODEV) and have_flag_in_mount(mnt, NOSUID) and have_flag_in_mount(mnt, NOEXEC)
    if not flags_ok:
        print(colors.yellow | f'missing flags in {mnt} mount')
        (echo[f'tmpfs {mnt} tmpfs rw,nosuid,nodev,noexec'] | tee['-a', '/etc/fstab'])()
        print(colors.yellow | f'fstab was modified. please reboot so the change will take an effect')
    else:
        print(colors.green | f'{mnt} is ok')


def check_dev_shm():
    mnt = DEV_SHM_MOUNT
    flags_ok = have_flag_in_mount(mnt, NODEV) and have_flag_in_mount(mnt, NOSUID) and have_flag_in_mount(mnt, NOEXEC)
    if not flags_ok:
        print(colors.red | f'mount {mnt} was not found or missing flags')
    else:
        print(colors.green | f'{mnt} is ok')


def have_mount(mnt):
    ch = mount | grep[mnt]
    return ch.run(retcode=None)[0] == 0


def check_removable():
    cdrom_is_bad = have_mount(CDROM) and (not have_flag_in_mount(CDROM, NODEV)
                                          or not have_flag_in_mount(CDROM, NOEXEC)
                                          or not have_flag_in_mount(CDROM, NOSUID))

    floppy_is_bad = have_mount(FLOPPY) and (not have_flag_in_mount(FLOPPY, NODEV)
                                            or not have_flag_in_mount(FLOPPY, NOEXEC)
                                            or not have_flag_in_mount(FLOPPY, NOSUID))

    if cdrom_is_bad or floppy_is_bad:
        print(colors.red | f'missing flag in removable media')
    else:
        print(colors.green | f'heuristics or removeable media is ok')


def main():
    check_tmp()
    check_var_tmp()
    check_dev_shm()
    check_removable()


if __name__ == '__main__':
    main()
