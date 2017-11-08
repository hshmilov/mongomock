"""PluginBase.py: Implementation of the base class to be inherited by other plugins."""

__author__ = "Ofir Yefet"

import json
import logging
import logging.handlers
from datetime import datetime
import sys
import traceback
import requests
import time
import inspect
import configparser
import os

from flask import Flask, request, jsonify
from flask.json import JSONEncoder
import json_log_formatter
from pymongo import MongoClient
from bson import ObjectId  # bson is requirement of mongo and its not recommended to install it manually
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from retrying import retry
from pathlib import Path

# Starting the Flask application
AXONIUS_REST = Flask(__name__)

LOG_PATH = str(Path.home().joinpath('logs'))  # this would be /home/axonius/logs, or c:\users\axonius\logs, etc.

# Can wait up to 5 minutes if core didnt answer yet
TIME_WAIT_FOR_REGISTER = 60*5


@AXONIUS_REST.after_request
def after_request(response):
    """This function is used to allow other domains to send post messages to this app.

    These headers are used to provide the cross origin resource sharing (cors) policy of this domain. 
    Modern browsers do not permit sending requests (especially post, put, etc) to differnet domains 
    without the explicit permission of the webserver on this domain. 
    This is why we have to add headers that say that we allow these methods from all domains.
    
    :param str docker_base_url: The response of the client (Will change is headers)

    :return: Fixed response that allow ither domain to send all methods
    """
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# Global list of all the functions we are registering.
ROUTED_FUNCTIONS = list()


def add_rule(rule, methods=['GET'], should_authenticate=True):
    """ Decorator for adding function to URL.

    This decorator will add a flask rule to a wanted method from a class derived
    From PluginBase

    :param str rule: The address. for example, if rule='device' 
            This function will be accessed when browsing '/device'
    :param methods: Methods that this function will handle
    :param bool should_authenticate: Wheather to check api key or not. True by default
    
    :type methods: list of str
    """

    def wrap(func):
        ROUTED_FUNCTIONS.append((func, rule, methods))

        def actual_wrapper(self, *args, **kwargs):
            """This wrapper will catch every exception.
            
            This wrapper will always cath exceptions from the decorated func. In that case, we return 
            the exception name with the Exception string.
            In case of exception, a detailed traceback will be sent to log
            """
            try:
                if should_authenticate:
                    # finding the api key
                    api_key = self.api_key
                    if api_key != request.headers.get('x-api-key'):
                        raise RuntimeError("Bad api key")
                return func(self, *args, **kwargs)
            except Exception as err:
                try:
                    # We excpect the first argument to be a PluginBase object (which have a logger object)
                    logger = getattr(self, "logger", None)
                    if logger:
                        # Adding exception details for the json logger
                        _, _, exc_traceback = sys.exc_info()
                        tb = repr(traceback.extract_tb(exc_traceback))
                        err_type = type(err).__name__
                        err_message = str(err)
                        extra_log = dict()
                        extra_log['err_traceback'] = tb
                        extra_log['err_type'] = err_type
                        extra_log['err_message'] = err_message
                        logger.error("Unhandled exception thrown from plugin", extra=extra_log)
                    return json.dumps({"status": "error", "type": err_type, "message": err_message}), 400
                except Exception as second_err:
                    return json.dumps({"status": "error", "type": type(second_err).__name__,
                                       "message": str(second_err)}), 400

        return actual_wrapper

    return wrap


class IteratorJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o.generation_time)
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, o)


def retry_if_connection_error(exception):
    """Return True if we should retry (in this case when it's an connection), False otherwise"""
    return isinstance(exception, requests.exceptions.ConnectionError)


def return_error(error_message, http_status=500):
    """ Helper function for returning errors in our format.

    :param str error_message: The explenation of the error
    :param int http_status: The http status to return, 500 by default
    """
    return jsonify({'status': 'error', 'message': error_message}), http_status


class PluginBase(object):
    """ This is an abstract class containing the implementation
    For the base capabilities of the Plugin.

    You should inherit this class from your Plugin class, and then use the decorator
    'add_rule' in order to add this rule to the URL.

    All Exceptions thrown from your decorated function will return as a response for
    The user request.

    """

    def __init__(self, core_data=None):
        """ Initialize the class.

        This will automatically add the rule of '/version' to get the Plugin version.

        :param str version: The version of this app
        :param dict core_data: A data sent by the core plugin. (Will skip the registration process)

        :raise KeyError: In case of environment variables missing
        """

        # Basic configurations conserning axonius-libs. This will be changed by the CI.
        # No need to put such a small thing in a version.ini file, the CI changes this string everywhere.
        self.lib_version = "%version%"

        # Getting values from configuration file
        config = configparser.ConfigParser()
        config.read('plugin_config.ini')
        self.version = config['DEFAULT']['version']
        self.plugin_name = config['DEFAULT']['name']
        self.plugin_unique_name = None
        self.api_key = None

        # Debug values. On production, flask is not the server, its just a wsgi app that uWSGI uses.
        try:
            self.host = config['DEBUG']['host']
            self.port = int(config['DEBUG']['port'])
        except KeyError:
            # This is the default value, which is what nginx sets for us.
            self.host = "0.0.0.0"
            self.port = 443  # We listen on https.

        # This is a debug value for setting a different core address.
        try:
            self.core_address = config['DEBUG']['core_address']
        except KeyError:
            self.core_address = "https://core"  # This should be dns resolved.

        try:
            self.plugin_unique_name = config['registration']['plugin_unique_name']
            self.api_key = config['registration']['api_key']
        except KeyError:
            # We might have api_key but not have a unique plugin name.
            pass

        if not core_data:
            core_data = self._register(self.core_address + "/register", self.plugin_unique_name, self.api_key)
        if not core_data or core_data['status'] == 'error':
            raise RuntimeError("Register process faild, Existing. Reason: {0}".format(core_data['message']))

        if core_data['plugin_unique_name'] != self.plugin_unique_name or core_data['api_key'] != self.api_key:
            self.plugin_unique_name = core_data['plugin_unique_name']
            self.api_key = core_data['api_key']
            config['registration']['plugin_unique_name'] = self.plugin_unique_name
            config['registration']['api_key'] = self.api_key

            # Writing back the configuration with the new plugin name
            with open('plugin_config.ini', 'w') as configfile:
                config.write(configfile)

        # Use the data we have from the core.

        self.db_host = core_data['db_addr'] 
        self.db_user = core_data['db_user']
        self.db_password = core_data['db_password']
        self.logstash_host = core_data['log_addr']

        self.log_path = LOG_PATH + '/' + self.plugin_unique_name + '.log'
        self.log_level = logging.INFO

        # Creating logger
        self.logger = self._create_logger(self.logstash_host, self.log_path)

        # Adding rules to flask
        for routed in ROUTED_FUNCTIONS:
            (wanted_function, rule, wanted_methods) = routed

            AXONIUS_REST.add_url_rule('/' + rule, rule,
                                      getattr(self, wanted_function.__name__),
                                      methods=wanted_methods)

        # Adding "keepalive" thread
        if self.plugin_unique_name != "core": 
            self.comm_failure_counter = 0
            executors = {'default': ThreadPoolExecutor(5)}
            self.scheduler = BackgroundScheduler(executors=executors)
            self.scheduler.start()
            self.scheduler.add_job(func=self._check_registered_thread,
                                   trigger=IntervalTrigger(seconds=1000),
                                   next_run_time=datetime.now(),
                                   id='check_registered',
                                   max_instances=1)

        # Creating open actions dict. This dict will hold all of the open actions issued by this plugin.
        # We will use this dict in order to determine what is the right callback for the action update retrieved.
        self._open_actions = dict()

        # Add some more changes to the app.
        AXONIUS_REST.json_encoder = IteratorJSONEncoder
        self.wsgi_app = AXONIUS_REST

        # Finished, Writing some log
        self.logger.info("Plugin {0}:{1} with axonius-libs:{2} started successfully. ".format(self.plugin_unique_name,
                                                                                              self.version,
                                                                                              self.lib_version))

    def wsgi_app(self, *args, **kwargs):
        """
        A proxy to our wsgi app. Should be used by anyone inheriting from PluginBase that wants access
        to the wsgi function, like uWSGI.
        :return: what the actual wsgi app returns.
        """

        return self.wsgi_app(*args, **kwargs)

    def _check_registered_thread(self):
        """Function for check that the plugin is still registered.

        This function will issue a get request to the Core to see if we are still registered.
        I case we arent, this function will stop this application (and let the docker manager to run it again)
        """
        try:
            response = self.request_remote_plugin("register?unique_name={0}".format(self.plugin_unique_name))
            if response.status_code == 404:
                self.logger.error("Not registered to core, Exiting")
                os._exit(1)  # TODO: Think about a better way for exiting this process
        except Exception as e:
            self.comm_failure_counter += 1
            if self.comm_failure_counter > 12:  # Two minutes
                self.comm_failure_counter = 0
                self.logger.error(("Error communicating with Core for more than 2 minutes, "
                                   "exiting. Reason: {0}").format(e))
                os._exit(1)

    @retry(wait_fixed=10*1000, 
           stop_max_delay=60*5*1000, 
           retry_on_exception=retry_if_connection_error)  # Try every 10 seconds for 5 minutes
    def _register(self, core_address, plugin_unique_name=None, api_key=None):
        """Create registration of the adapter to core.

        :param str core_address: The address of the core plugin
        :param str plugin_unique_name: Wanted name of the plugin(Optional)
        :param str api_key: Api key to use in case we want a certain plugin_unique_name
        :return requests.response: The register response from the core
        """
        register_doc = {"plugin_name": self.plugin_name,
                        "plugin_type": self.plugin_type,
                        "plugin_port": self.port
                        }
        if plugin_unique_name:
            register_doc['plugin_unique_name'] = plugin_unique_name
            if api_key:
                register_doc['api_key'] = api_key
        
        response = requests.post(core_address, data=json.dumps(register_doc))
        return response.json()

    def _create_logger(self, logstash_host, log_path):
        """ Creating Json logger.

        Creating a logging object to be used by the plugin. This object is the pythonic logger object
        And can be used the same. The output file of the logs will be in a JSON format and will be entered to
        An ELK stack.

        :param str logstash_host: The address of logstash HTTP interface.
        :param str log_path: The path for the log file.
        """
        plugin_unique_name = self.plugin_unique_name

        # Custumized logger formatter in order to enter some extra fields to the log message
        class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
            def json_record(self, message, extra, record):
                try:
                    extra['level'] = record.levelname
                    extra['message'] = message
                    extra['plugin_unique_name'] = plugin_unique_name
                    current_time = datetime.utcfromtimestamp(record.created)
                    extra['@timestamp'] = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

                    # Adding the frame details of the log message. 
                    # This is in a different try because failing in this process does 
                    # not mean failing in the format process, so we need a 
                    # different handling type for error in this part
                    try:
                        frame_stack = inspect.stack()
                        # Currently we have a list with all frames. The first 2 frames are this logger frame, 
                        # The next lines are the pythonic library. We want to skip all of these frames to reach 
                        # the first frame that is not logging function. This is the function that created
                        # this log message.
                        for current_frame in frame_stack[3:]:  # Skipping the first two lines (belogs to the formatter)
                            if (("lib" in current_frame.filename and "logging" in current_frame.filename) or
                                        current_frame.function == 'emit'):
                                # We are skipping this frame because it belongs to the pythonic logging lib. or
                                # It belongs to the emit function (the function that sends the logs to logstash)
                                continue
                            else:
                                # This is the frame that we are looking for (The one who initiated a log print)
                                extra['funcName'] = current_frame.function
                                extra['lineNumber'] = current_frame.lineno
                                extra['filename'] = current_frame.filename
                                break
                    except Exception:
                        pass
                except Exception:
                    # We are doing the minimum in order to make sure that this log formmating won't fail
                    # And that we will be able to send this message anyway
                    extra = dict()
                    extra['level'] = "CRITICAL"
                    extra['message'] = "Error in json formatter, not writing log"
                    extra['plugin_unique_name'] = plugin_unique_name
                return extra

        fatal_log_path = log_path.split('.log')[0] + '_FATAL.log'
        file_handler_fatal = logging.handlers.RotatingFileHandler(fatal_log_path,
                                                                  maxBytes=50 * 1024 * 1024,  # 150Mb Max
                                                                  backupCount=3)
        formatter = CustomisedJSONFormatter()
        file_handler_fatal.setFormatter(formatter)
        fatal_logger = logging.getLogger('axonius_plugin_fatal_log')
        fatal_logger.addHandler(file_handler_fatal)
        fatal_logger.setLevel(self.log_level)

        # Custummized logger handler in order to send logs to logstash using http
        class LogstashHttpServer(logging.Handler):
            def __init__(self, **kargs):
                """
                    Logging handler for connecting logstash through http.
                """
                self.bulk_size = 100  # lines
                self.max_time = 30  # Secs
                self.error_cooldown = 120  # Secs
                self.max_logs = 100000  # lines
                self.warning_before_cooldown = 3
                self.currentLogs = []
                self.last_sent = time.time()
                self.last_error_time = 0
                super().__init__()

            def emit(self, record):
                """ The callback that is called in each log message.
                
                This function will actually send the log to logstash. I order to be more efficient, log messages are
                Not sent directly but instead this function saves a bulk of log messages and then send them together.
                This will avoid the TCP/SSL connection overhead.
                Since we cant send a bulk of messages in one http request (Logstash do not support this) we will create
                One TCP session (with keep alive) and post messages one by one.
                """
                try:
                    log_entry = self.format(record)
                    current_time = time.time()

                    # Checking if we can append the new log entry
                    if len(self.currentLogs) < self.max_logs:
                        self.currentLogs.append(log_entry)

                    # Checking if we need to dump logs to the server
                    if ((len(self.currentLogs) > self.bulk_size or
                       current_time - self.last_sent > self.max_time) and
                       current_time - self.last_error_time > self.max_time):
                        self.last_sent = current_time
                        with requests.Session() as s:  # Sending all logs on one session
                            new_list = []
                            # The warning count will count how much time we couldnt save a log due to an error.
                            # In case of too much errors (defined by 'warning_before_cooldown') we will enter
                            # some cooldown period (defined by 'error_cooldown')
                            warning_count = 0
                            for log_line in self.currentLogs:
                                try:
                                    if warning_count > self.warning_before_cooldown:
                                        # Something bad with the connection, not trying to send anymore. Just append
                                        # All the messages that we couldnt send
                                        new_list.append(log_line)
                                    else:
                                        s.post(logstash_host, data=log_line, timeout=2)

                                except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout,
                                        requests.exceptions.InvalidSchema):
                                    # We should add this log line again to the list because the problem
                                    # Is in the connection and not in the log
                                    new_list.append(log_line)
                                    warning_count = warning_count + 1
                                except Exception as e:
                                    exception_log = "Error while sending log. *Log is lost*. Error details: " \
                                                    "type={0}, message={1}".format(type(e).__name__, str(e))
                                    print("[fatal error]: %s" % (exception_log, ))
                                    fatal_logger.error(exception_log)
                                    warning_count = warning_count + 1
                                    continue
                                    # In any other cases, we should just try the other log lines 
                                    # (This line will not be sent anymore)
                            if warning_count != 0:
                                warning_message = "connection error occured {0} times while sending log."\
                                    .format(warning_count)
                                print("[fatal error]: %s." % (warning_message, ))
                                fatal_logger.warning(warning_message)
                                if warning_count > self.warning_before_cooldown:
                                    self.last_error_time = time.time()
                            self.currentLogs = new_list
                        return ''
                except Exception as e:  # We must catch every exception from the logger
                    # Nothing we can do here
                    exception_message = "Error on logger Error details: type={0}, message={0}".format(type(e).__name__, str(e))
                    print("[fatal error]: %s" % (exception_message, ))
                    fatal_logger.error(exception_message)
                    return 'Bad'

        # Creating the logger using our custumized logger fomatter
        formatter = CustomisedJSONFormatter()
        # Creating a rotating file log handler
        file_handler = logging.handlers.RotatingFileHandler(log_path,
                                                            maxBytes=50 * 1024 * 1024,  # 150Mb Max
                                                            backupCount=3)
        file_handler.setFormatter(formatter)

        # Creating logstash file handler (implemeted above)
        logstash_handler = LogstashHttpServer()
        logstash_handler.setFormatter(formatter)

        # Building the logger object
        logger = logging.getLogger('axonius_plugin_log')
        logger.addHandler(file_handler)
        logger.addHandler(logstash_handler)
        logger.setLevel(self.log_level)

        return logger

    def start_serve(self):
        """Start Http server.
        
        This function is blocking as long as the Http server is up.
        .. warning:: Do not use it in production! nginx->uwsgi is the one that loads us on production, so it does not call start_serve.
        """
        AXONIUS_REST.run(host=self.host, port=self.port, debug=False, use_reloader=False)

    def get_method(self):
        """Getting the method type of the request.

        :return: The method type of the current request
        """
        return request.method

    def get_url_param(self, param_name):
        """ Getting params from the URL entered.

        This function is getting parameters only from the URL. For example '/somthing?param1=somthing'

        :param str param_name: The name of the parameters we want to get

        :return: The value of the wanted parameter
        """
        return request.args.get(param_name)

    def get_request_header(self, header_name):
        return request.headers.get(header_name)

    def get_request_data(self):
        """Get the data (raw) from the request.

        :return:The content of the post request
        """
        return request.data

    def get_request_data_as_object(self):
        """ Get data from HTTP request as python object.

        :return: The contest of the post request as a python object (An output of the json.loads function)
        """
        post_data = self.get_request_data()
        if post_data:
            decodedData = post_data.decode('utf-8')  # To make it string instead of bytes
            data = json.loads(decodedData)
            return data
        else:
            return None

    def get_caller_plugin_name(self):
        """
        Figures out who called us from
        :return: tuple(plugin_unique_name, plugin_name)
        """
        return request.headers.get('x-unique-plugin-name'), request.headers.get('x-plugin-name')

    def request_remote_plugin(self, resource, plugin_unique_name=None, method='get', **kwargs):
        """
        Provides an interface to access other plugins, with the current plugin's API key.
        :type resource: str
        :param resource: The resource (e.g. 'devices' or 'version') of the plugin
        :type plugin_unique_name: str
        :param plugin_unique_name: The unique name of the plugin in question. None will make a request to the core.
        :param method: HTTP method - see `request.request`
        :param kwargs: passed to `requests.request`
        :return: :class:`Response <Response>` object
        :rtype: requests.Response
        """
        headers = {'x-api-key': self.api_key}
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']  # this does not change the original dict given to this method

        if plugin_unique_name is None:
            url = '{}/{}'.format(self.core_address, resource)
        else:
            url = '{}/{}/{}'.format(self.core_address, plugin_unique_name, resource)

        return requests.request(method, url,
                                headers=headers, **kwargs)

    def create_notification(self, title, content, notification_type='basic'):
        """
        Creates a notification (to be seen by the user in the GUI)
        :param title: A short title of the notification, e.g. "Device has found to be infected!"
        :param content: The content of the notification
        :param notification_type: tbd
        :return: _id of the notification in the db
        """
        with self._get_db_connection(True) as db:
            return db['core']['notifications'].insert_one(dict(
                who=self.plugin_unique_name,
                plugin_name=self.plugin_name,
                type=notification_type,
                title=title,
                content=content,
                seen=False)).inserted_id

    @add_rule('version', methods=['GET'], should_authenticate=False)
    def _get_version(self):
        """ /version - Get the version of the app.
        
        Accepts:
            GET - In order to retrieve the plugin version
        """

        version_object = {"plugin": self.version, "axonius-libs": self.lib_version}

        return jsonify(version_object)

    @add_rule('logger', methods=['GET', 'PUT'])
    def _logger_func(self):
        """ /logger - In order to change logger settings

        Accepts:
            GET - In order to get the current logger details (currently just logging level)
            PUT - In order to change logger details. available params:
                'level': The wanted logging level (string)
        """
        logging_types = {'debug': logging.DEBUG,
                         'info': logging.INFO,
                         'warning': logging.WARNING,
                         'error': logging.ERROR,
                         'fatal': logging.FATAL}
        if self.get_method() == 'PUT':
            wanted_level = self.get_url_param('level')
            if wanted_level is None:
                return return_error("missing wanted_level parameter", 400)
            wanted_level = wanted_level.lower()
            if wanted_level in logging_types.keys():
                self.log_level = logging_types[wanted_level]
                self.logger.setLevel(self.log_level)
                return ''
            else:
                error_string = "Unsupprted log level \"{wanted_level}\", available log levels are {levels}"
                return return_error(error_string.format(wanted_level=wanted_level, levels=logging_types.keys()), 400)
        else:
            return logging.getLevelName(self.log_level)

    @add_rule('action_update/<action_id>', methods=['POST'])
    def action_callback(self, action_id):
        """ A function for receiving updates from the executor (Adapter or EC).

        This function will listen on updates, and if the update is on a relevant action_id it will call the 
        Callback registered for this action.

        Accepts:
            POST - For posting a status update (or sending results) on a specific action
        """
        if action_id not in self._open_actions:
            if self.plugin_name == "execution_controller":
                # This is a special case for the execution_controller plugin. In that case, The EC plugin knows how to 
                # handle other actions such as reset_update. In case of ec plugin, we know for sure what is the 
                # callback, we use this fact to just call the callback and not search for it on the _open_actions 
                # list (because the current action id will not be there)
                self.ec_callback(action_id)
                return ''
            else:
                self.logger.error('Got unrecognized action_id update. Action ID: {0}'.format(action_id))
                return self.return_error('Unrecognized action_id {0}'.format(action_id), 404)
        else:
            # We recognize this action id, should call its callback
            callback_function = self._open_actions[action_id]
            # Calling the needed function
            callback_function(action_id)
            return ''

    def request_action(self, action_type, axon_id, callback_function, data_for_action=None):
        """ A function for requesting action.

        This function called be used by any plugin. It will initiate an action request from the EC

        :param str action_type: The type of the action. For example 'put_file'
        :param str axon_id: The axon id of the device we want to run action on
        :param func callback_function: A pointer to the callback function. This function will be called on each update
                                       On this action id.
        :param dict data_for_action: Extra data for executing the wanted action.

        :return result: the result of the request (as returned from the REST request)
        """
        if data_for_action:
            data = data_for_action.copy()

        # Building the uri for the request
        uri = 'action/{action_type}?axon_id={axon_id}&issuer_name={issuer}'.format(action_type=action_type,
                                                                                   axon_id=axon_id,
                                                                                   issuer=self.plugin_unique_name)
            
        result = self.request_remote_plugin(uri,
                                            plugin_unique_name='execution_controller',
                                            method='POST', 
                                            data=json.dumps(data))

        action_id = result.json()['action_id']

        self._open_actions[action_id] = callback_function

        return result

    def _get_db_connection(self, limited_user):
        """
        Returns a new DB connection that can be queried.
        Currently, it uses mongodb

        :return: MongoClient
        """
        if limited_user:
            pure_addr = self.db_host.split("mongodb://")[1]
            connection_line = "mongodb://{user}:{password}@{addr}/{db}".format(user=self.db_user,
                                                                               password=self.db_password,
                                                                               addr=pure_addr,
                                                                               db=self.plugin_unique_name)
            return MongoClient(connection_line)
        else:
            return MongoClient(self.db_host, username=self.db_user, password=self.db_password)

    def _get_collection(self, collection_name, db_name=None, limited_user=True):
        """
        Returns all configs for the current plugin.

        :param str collection_name: The name of the collection we want to get
        :param str db_name: The name of the db. By default it is the unique plugin name

        :return: list(dict)
        """
        if not db_name:
            db_name = self.plugin_unique_name
        return self._get_db_connection(limited_user)[db_name][collection_name]

    @add_rule('schema/<schema_type>', methods=['GET'])
    def schema(self, schema_type):
        """ /schema - Get the schema the plugin expects from configs. 
                      Will try to get the wanted schema according to <schema_type>

        Accepts:
            GET - Get schema. name of the schema is given in the url. 
                  For example: "http://<address>/schema/general_schema

        :return: list(str)
        """
        schema_type = "_" + schema_type + "_schema"
        if schema_type in dir(self):
            # We have a schema like this
            schema_func = getattr(self, schema_type)
            return jsonify(schema_func())
        else:
            self.logger.warning("Someone tried to get wrong schema '{0}'".format(schema_type))
            return return_error("No such schema. should implement {0}".format(schema_type), 400)

    def _general_schema(self):
        """
        Represents the set of keys the plugin expects from general config

        :return: JSON Schema
        """

        return {}

    @property
    def plugin_type(self):
        return "Plugin"
