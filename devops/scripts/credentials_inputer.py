import sys
import os

try:
    from devops.scripts.fast_axonius.fast_axonius import fast_axonius
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'plugins', 'axonius-libs',
                                                 'src', 'libs', 'axonius-py')))
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'testing')))
    from devops.scripts.fast_axonius.fast_axonius import fast_axonius


def main():
    ax = fast_axonius()
    for current_service in ax._services.values():
        if current_service.is_up():
            current_service.set_client()


if __name__ == '__main__':
    main()
