import sys

from passlib.hash import bcrypt

from services.axonius_service import AxoniusService


def main():
    ax = AxoniusService()
    users_collection = ax.db.gui_users_collection()
    users_collection.update_one(
        {
            'user_name': 'admin'
        },
        {
            '$set': {
                'password': bcrypt.hash('Xjn28$maP')
            }
        }
    )


if __name__ == '__main__':
    main()
