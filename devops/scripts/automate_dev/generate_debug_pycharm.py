from devops.scripts.fast_axonius.fast_axonius import fast_axonius


def main():
    ax = fast_axonius()
    for service in list(ax._services.values()) + list(ax._plugins.values()):
        if hasattr(service, 'generate_debug_template'):
            service.generate_debug_template()


if __name__ == '__main__':
    main()
