import services.mongo_service as db
import services.core_service as core
import services.aggregator_service as aggregator
import services.gui_service as gui

import argparse
import sys
import importlib


def start():
    db.MongoService().start_and_wait()
    core.CoreService().start_and_wait()
    aggregator.AggregatorService().start_and_wait()
    gui.GuiService().start_and_wait()


def stop():
    gui.GuiService().stop(should_delete=False)
    aggregator.AggregatorService().stop(should_delete=False)
    core.CoreService().stop(should_delete=False)
    db.MongoService().stop(should_delete=False)


def start_plugin(plugin_name):
    plugin = invoke_plugin_by_name(plugin_name)
    plugin.start_and_wait()


def stop_plugin(plugin_name):
    plugin = invoke_plugin_by_name(plugin_name)
    plugin.stop(should_delete=False)


def invoke_plugin_by_name(plugin_name):
    plugin_service = importlib.import_module("services.{}_service".format(plugin_name.lower()))
    plugin_service = getattr(plugin_service, plugin_name + "Service")()
    return plugin_service


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Axonius system startup')
    parser.add_argument('system', choices=['up', 'down'])
    parser.add_argument('--plugins', metavar='N', type=str, nargs='*', help='Plugins to activate')
    parser.add_argument('--adapters', metavar='N', type=str, nargs='*', help='Plugins to activate')

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    if args.system == 'up':
        start()
        if args.plugins:
            for plugin in args.plugins:
                start_plugin(plugin)
        if args.adapters:
            for adapter in args.adapters:
                start_plugin(adapter)
    else:
        if args.adapters:
            for adapter in args.adapters:
                stop_plugin(adapter)
        if args.plugins:
            for plugin in args.plugins:
                stop_plugin(plugin)
        stop()
