import sys

from passlib.hash import bcrypt

from axonius.consts.plugin_consts import AXONIUS_USER_NAME
from services.axonius_service import AxoniusService


def main(new_password):
    ax = AxoniusService()
    users_collection = ax.db.gui_users_collection()
    users_collection.update_one(
        {
            'user_name': AXONIUS_USER_NAME
        },
        {
            '$set': {
                'password': bcrypt.hash(new_password)
            }
        }
    )


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('python add_master_password.py <new_password>')
    main(sys.argv[1])
