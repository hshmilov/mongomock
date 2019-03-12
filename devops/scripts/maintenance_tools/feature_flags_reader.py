import json
from services.plugins.gui_service import GuiService


def main():
    gs = GuiService()
    print(json.dumps(gs.get_feature_flags()))


if __name__ == '__main__':
    main()
