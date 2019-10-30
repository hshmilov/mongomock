from plumbum.cmd import lsmod, grep, rmmod
from plumbum import colors

# cis section 1.1.1 - unused fs

modules = ['cramfs', 'freevxfs', 'jffs2', 'hfs', 'hfsplus', 'udf']


def is_module_not_installed(module):
    ch = lsmod | grep[module]
    return ch.run(retcode=None)[0] == 1


def main():
    print(f'Checking for unused filesystems')
    for module in modules:
        ret = is_module_not_installed(module)
        if ret:
            print(colors.green | f'{module} not installed ')
        else:
            print(colors.yellow | f'{module} is present')
            try:
                rmmod[module]()
                print(f'removed {module}')
            except Exception as e:
                print(colors.red | f'failed to remove {module} - {e}')


if __name__ == '__main__':
    main()
