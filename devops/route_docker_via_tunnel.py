import sys

from conf_tools import set_docker_as_tunneled


def main():
    adapter_docker_name = sys.argv[1]
    set_docker_as_tunneled(adapter_name=adapter_docker_name)
    print(f'Docker {adapter_docker_name} marked to be tunneled. Please restart the adapter with ./axonius.sh')


if __name__ == '__main__':
    main()
