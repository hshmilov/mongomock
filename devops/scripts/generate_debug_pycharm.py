import sys
import os

try:
    from devops.scripts.fast_axonius.fast_axonius import fast_axonius
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'axonius-libs',
                                                 'src', 'libs', 'axonius-py')))
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'testing')))
    from devops.scripts.fast_axonius.fast_axonius import fast_axonius


def main():
    ax = fast_axonius()
    for service in list(ax._services.values()) + list(ax._plugins.values()):
        if hasattr(service, 'generate_debug_template'):
            service.generate_debug_template()


if __name__ == '__main__':
    main()
