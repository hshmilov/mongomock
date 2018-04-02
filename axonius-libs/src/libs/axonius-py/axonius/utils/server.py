"""
Utility functions for any server-related activities, i.e. a flask server, wsgi things, etc.
"""
import functools
import threading

lock = threading.Lock()


def init_wsgi(plugin_object):
    """
    Initializes env if we run in wsgi, else doesn't do anything.

    The following function should be called from any file that a wsgi component (like uwsgi) loads.
    It should be called from the main context (no if __name___ == '__main__' flow...)

    How to use: from the main context, write:
    wsgi_app = init_wsgi(plugin) # plugin is a PluginBase object

    :param plugin_object: The plugin class (a PluginBase) we wish to run.
    :return: a wsgi object or None.
    """

    def wsgi_main(plugin_object, *args, **kwargs):
        """The main method for wsgi apps.

        When in production mode, we use a production server with wsgi support to load our modules.
        so we use this function as a proxy to the real wsgi function flask provides.
        """

        with lock:
            if not hasattr(wsgi_main, "plugin"):
                wsgi_main.plugin = plugin_object()

        return wsgi_main.plugin.wsgi_app(*args, **kwargs)

    return functools.partial(wsgi_main, plugin_object)
