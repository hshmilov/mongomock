from plumbum.cmd import systemctl
from plumbum import colors


# cis section 1.1.20 - autofs

def main():
    res = systemctl['is-enabled', 'autofs'].run(retcode=None)[1]  # stdout
    if 'enabled' in res:
        print(colors.yellow | 'autofs was enabled')
        try:
            systemctl['disable', 'autofs']()
        except Exception as e:
            print(colors.red | f'disable autofs failed {e}')
    else:
        print(colors.green | 'automount is disabled')


if __name__ == '__main__':
    main()
