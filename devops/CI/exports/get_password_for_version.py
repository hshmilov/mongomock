import sys

from CI.exports.version_passwords import VersionPasswords


def main():
    version = sys.argv[1]
    password = VersionPasswords().get_password_for_version(version)
    print(f'password for {version} is {password}')


if __name__ == '__main__':
    main()
