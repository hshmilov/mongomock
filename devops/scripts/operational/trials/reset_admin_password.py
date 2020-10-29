from axonius.utils.hash import user_password_handler
from services.axonius_service import AxoniusService


def main():
    ax = AxoniusService()
    users_collection = ax.db.gui_users_collection()
    password, salt = user_password_handler('Xjn28$maP')
    users_collection.update_one(
        {
            'user_name': 'admin'
        },
        {
            '$set': {
                'password': password,
                'salt': salt
            }
        }
    )


if __name__ == '__main__':
    main()
