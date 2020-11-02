import argparse

import testing.test_credentials.test_gui_credentials


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--internal', type=bool, default=False, help='Only set Axonius\'s users creds', required=False)
    args = parser.parse_args()
    testing.test_credentials.test_gui_credentials.axonius_set_test_passwords(args.internal)


if __name__ == '__main__':
    print('Changing Axonius passwords to test passwords.')
    main()
