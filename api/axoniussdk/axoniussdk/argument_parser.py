import argparse


class ArgumentFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


DEFAULT_AXONIUS_URL = 'https://localhost'
DEFAULT_USERNAME = 'admin'


class ArgumentParser(argparse.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formatter_class = ArgumentFormatter
        self.description = \
            '''Example:
  %(prog)s -x https://axnoius.local --username admin -p password1 --no-verify-ssl
  %(prog)s -x https://axnoius.local --api-key xxxx --api-secret yyyy'''

        self.add_argument('--axonius-url', '-x', help='axonius gui url',
                          default=DEFAULT_AXONIUS_URL)

        auth_group = self.add_argument_group('Auth')

        auth_group.add_argument('--username', '-u', help='system username', default=DEFAULT_USERNAME)
        auth_group.add_argument('--password', '-p')
        auth_group.add_argument('--api-key')
        auth_group.add_argument('--api-secret')

        self.add_argument('--no-verify-ssl', '-s', action='store_true', default=False,
                          help='Don\'t verify ssl')
        self.add_argument('--logfile', '-l')

    def parse_args(self, args=None, namespace=None):
        args = super().parse_args(args, namespace)
        if bool(args.api_key) != bool(args.api_secret):
            self.error('--api-key requires --api-secret')
        if len(list(filter(bool, (args.api_secret, args.password)))) != 1:
            self.error('one of the arguments --password --api-secret is required')
        if len(list(filter(bool, (args.api_key, args.password)))) != 1:
            self.error('one of the arguments --password --api-key is required')

        args.auth = None
        args.headers = None
        if args.username and args.password:
            args.auth = (args.username, args.password)
        else:
            args.headers = {'api-key': args.api_key,
                            'api-secret': args.api_secret}
        return args
