import urllib.request  # no venv needed, please keep it that way


def get_latest_ami():
    return urllib.request.urlopen(
        'https://axonius-releases.s3.us-east-2.amazonaws.com/latest_release/ami_id.txt').read().decode().strip()


def get_latest_version():
    return urllib.request.urlopen(
        'https://axonius-releases.s3.us-east-2.amazonaws.com/latest_release/version_name.txt').read().decode().strip()


def main():
    print(get_latest_ami())


if __name__ == '__main__':
    main()
