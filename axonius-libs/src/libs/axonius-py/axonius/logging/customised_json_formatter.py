import json_log_formatter
from datetime import datetime
import inspect
import traceback
from pathlib import Path
import json
from flask import has_request_context, session, request

from axonius.consts import system_consts
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, X_UI_USER, X_UI_USER_SOURCE, METADATA_PATH

MAX_LOG_MESSAGE_LEN = 1024 * 4
LOGGER_LIB_STACKTRACE_PATTERN = 'File "/usr/lib/python3.6/logging/'


def read_version():
    try:
        path = METADATA_PATH
        if not path.is_file():
            path = system_consts.METADATA_PATH
        metadata = Path(path).read_text()
        return json.loads(metadata)['Version']
    except Exception:
        print(f'WARNING: Failed to read metadata to extract version info. \n'
              f'It is not fatal if happens in non prod env \n'
              f'{traceback.format_exc()}')
    return ''


VERSION = read_version()


# Custumized logger formatter in order to enter some extra fields to the log message
class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
    def __init__(self, plugin_unique_name, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        self.plugin_unique_name = plugin_unique_name

    def json_record(self, message, extra, record):
        try:
            extra['level'] = record.levelname
            extra['thread'] = record.thread

            if VERSION:
                extra['version'] = VERSION

            if len(message) < MAX_LOG_MESSAGE_LEN:
                extra['message'] = message
            else:
                extra['message'] = message[:MAX_LOG_MESSAGE_LEN]
                extra['truncated'] = True

            if record.exc_info:
                # split to stack trace and the specific message
                formatted = self.formatException(record.exc_info).split('\n')
                extra['exc_info'] = "\n".join(formatted[:-1])
                extra['exception_message'] = formatted[-1]
                try:
                    # Sometimes, just the stack trace isn't enough, since the message is generated in a try/except
                    # which we have no idea how we got into. so we print the full call stack
                    stack = traceback.format_stack()
                    stack = [line for line in stack if LOGGER_LIB_STACKTRACE_PATTERN not in line]
                    extra['full_callstack'] = ''.join(stack)
                except Exception:
                    pass
            extra[PLUGIN_UNIQUE_NAME] = self.plugin_unique_name
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
                # Skipping the first two lines (belogs to the formatter)
                for current_frame in frame_stack[3:]:
                    if (("lib" in current_frame.filename and "logging" in current_frame.filename) or
                            current_frame.function == 'emit'):
                        # We are skipping this frame because it belongs to the pythonic logging lib. or
                        # It belongs to the emit function (the function that sends the logs to logstash)
                        continue
                    else:
                        # This is the frame that we are looking for (The one who initiated a log print)
                        function = current_frame.function
                        line = current_frame.lineno
                        filename = current_frame.filename
                        extra['location'] = f"{filename}:{function}:{line}"

                        break

                if has_request_context():
                    user = session.get('user', {}).get('user_name')
                    if user:
                        extra['ui_user'] = user
                    elif request.headers.get(X_UI_USER):
                        extra['ui_user'] = request.headers.get(X_UI_USER)

                    source = session.get('user', {}).get('source')
                    if source:
                        extra['ui_user_source'] = source
                    elif request.headers.get(X_UI_USER_SOURCE):
                        extra['ui_user_source'] = request.headers.get(X_UI_USER_SOURCE)

            except Exception:
                pass
        except Exception:
            # We are doing the minimum in order to make sure that this log formmating won't fail
            # And that we will be able to send this message anyway
            extra = dict()
            extra['level'] = "CRITICAL"
            extra['message'] = "Error in json formatter, not writing log"
            extra[PLUGIN_UNIQUE_NAME] = self.plugin_unique_name
        return extra
