import sys

from builds import Builds
from builds.builds_factory import BuildsInstance


def ssh_example(instance: BuildsInstance):
    """
    ssh example
    :param instance: The instance
    :return: True.
    :exception: If anything bad happens.
    """
    print(f'Ifconfig: ')
    rc, output = instance.ssh('ifconfig')
    print(f'Return code: {rc}')
    print(f'Stdout: {output}')
    print(f'/etc/hosts:')
    print(instance.get_file('/etc/hosts'))


def main():
    bo = Builds()
    print(f'Latest exports: ')
    print(bo.get_last_exports())
    try:
        instances, group_name = bo.create_instances(f'Test GCP', 'n1-standard-2', 1)
        print(f'Created group name {group_name}')
        for instance in instances:
            instance.wait_for_ssh()
            ssh_example(instance)
    finally:
        bo.terminate_all()


if __name__ == '__main__':
    sys.exit(main())
