import sys

from services.axonius_service import AxoniusService


def main():
    ax = AxoniusService()
    users_collection = ax.db.gui_users_collection()
    users_collection.delete_one(
        {
            'user_name': 'admin'
        }
    )


if __name__ == '__main__':
    sys.exit(main())
