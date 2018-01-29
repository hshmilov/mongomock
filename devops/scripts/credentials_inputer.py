from devops.scripts.fast_axonius.fast_axonius import fast_axonius


def main():
    ax = fast_axonius()
    for current_service in ax._services.values():
        if current_service.is_up():
            current_service.set_client()


if __name__ == '__main__':
    main()
