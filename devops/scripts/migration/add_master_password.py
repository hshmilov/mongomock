import argparse
from passlib.hash import bcrypt

from axonius.consts.plugin_consts import AXONIUS_USER_NAME
from axonius.utils.hash import user_password_handler
from services.axonius_service import AxoniusService


def main(args):
    new_password = args.password
    username = args.username
    ax = AxoniusService()
    users_collection = ax.db.gui_users_collection()
    password, salt = user_password_handler(new_password)
    users_collection.update_one(
        {
            'user_name': username
        },
        {
            '$set': {
                'password': password,
                'salt': salt
            }
        }
    )


def read_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('password')
    parser.add_argument('--username', default=AXONIUS_USER_NAME, required=False)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main(read_args())
