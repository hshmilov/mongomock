#!/usr/bin/env python3

import argparse
import sys

from testing.services.plugins.gui_service import GuiService


def main(args):
    print(args)

    if args.read:
        print('Reading:')
        print(GuiService().get_maintenance_flags())
    else:
        set_maintanence_in_db(provision=args.provision,
                              analytics=args.analytics,
                              troubleshooting=args.troubleshooting)


def set_maintanence_in_db(provision, analytics, troubleshooting):
    gs = GuiService()
    flags = gs.get_maintenance_flags()

    print(provision, analytics, troubleshooting)

    if provision is not None:
        flags['provision'] = provision == 'True'
    if analytics is not None:
        flags['analytics'] = analytics == 'True'
    if troubleshooting is not None:
        flags['troubleshooting'] = troubleshooting == 'True'

    gs.set_maintenance_flags(flags)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--provision', choices=[None, 'True', 'False'], default=None)
    parser.add_argument('-a', '--analytics', choices=[None, 'True', 'False'], default=None)
    parser.add_argument('-t', '--troubleshooting', choices=[None, 'True', 'False'], default=None)
    parser.add_argument('-read', action='store_true')

    try:
        args = parser.parse_args()
    except Exception:
        print(parser.usage())
        sys.exit(1)
    return args


if __name__ == '__main__':
    args = parse_args()

    main(args)
