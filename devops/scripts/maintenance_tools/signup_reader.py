import json
from services.plugins.gui_service import GuiService


def main():
    gs = GuiService()
    data = gs.get_signup_collection().find_one()
    del data['_id']
    print(json.dumps(data))


if __name__ == '__main__':
    main()
