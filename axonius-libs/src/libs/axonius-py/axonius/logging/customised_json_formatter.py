import json_log_formatter
from datetime import datetime
import inspect
import traceback
from flask import has_request_context, session

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


# Custumized logger formatter in order to enter some extra fields to the log message
class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
    def __init__(self, plugin_unique_name, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        self.plugin_unique_name = plugin_unique_name

    def json_record(self, message, extra, record):
        try:
            extra['level'] = record.levelname
            extra['thread'] = record.thread
            extra['message'] = message
            if record.exc_info:
                # split to stack trace and the specific message
                formatted = self.formatException(record.exc_info).split('\n')
                extra['exc_info'] = "\n".join(formatted[:-1])
                extra['exception_message'] = formatted[-1]
                try:
                    # Sometimes, just the stack trace isn't enough, since the message is generated in a try/except
                    # which we have no idea how we got into. so we print the full call stack
                    extra['full_callstack'] = ''.join(traceback.format_stack())
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
                        extra['funcName'] = current_frame.function
                        extra['lineNumber'] = current_frame.lineno
                        extra['filename'] = current_frame.filename
                        extra['location'] = f"{extra['filename']}:{extra['funcName']}:{extra['lineNumber']}"

                        break

                if has_request_context():
                    user = session.get('user', {}).get('user_name')
                    if user:
                        extra['ui_user'] = user

                    source = session.get('user', {}).get('source')
                    if source:
                        extra['ui_user_source'] = source

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
