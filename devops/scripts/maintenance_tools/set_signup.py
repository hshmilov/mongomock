from services.plugins.gui_service import GuiService

SIGNUP_TEST_CREDS = {'company': 'test_company', 'password': 'cAll2SecureAll', 'email': 'a@b.com'}


def main():
    gs = GuiService()
    signup_collection = gs.get_signup_collection()
    signup_collection.drop()
    signup_collection.insert_one(SIGNUP_TEST_CREDS)


if __name__ == '__main__':
    main()
