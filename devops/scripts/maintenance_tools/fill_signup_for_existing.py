import argparse

from axonius.consts.gui_consts import Signup
from services.plugins.gui_service import GuiService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--company', type=str, help='company name', required=True)

    args = parser.parse_args()

    signup_dict = {Signup.CompanyField: args.company}

    gs = GuiService()
    signup_collection = gs.get_signup_collection()
    if len(list(signup_collection.find({}))) == 0:
        signup_collection.insert_one(signup_dict)
        print(f'setting signup to {signup_dict}')
    else:
        print('signup already set')


if __name__ == '__main__':
    main()
