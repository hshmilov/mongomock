"""
Helps with all sorts of CI-Related things.
"""
import sys
import threading

from teamcity import is_running_under_teamcity
from teamcity.messages import TeamcityServiceMessages


# TextIOWrapper objects like sys.stdout are not thread-safe (https://docs.python.org/3.4/library/io.html)
class BufferedWriterThreadSafe:
    def __init__(self, buffered_writer):
        self.buffered_writer = buffered_writer
        self.buffered_writer_lock = threading.Lock()

    def flush(self, *args, **kwargs):
        with self.buffered_writer_lock:
            self.buffered_writer.flush(*args, **kwargs)

    def write(self, *args, **kwargs):
        with self.buffered_writer_lock:
            self.buffered_writer.write(*args, **kwargs)
            self.buffered_writer.flush()


class TextIOWrapperThreadSafe:
    def __init__(self, io_wrapper):
        self.buffer = BufferedWriterThreadSafe(io_wrapper.buffer)


class TeamcityHelper(TeamcityServiceMessages):
    def __init__(self):
        super().__init__(output=TextIOWrapperThreadSafe(sys.stdout))

    @staticmethod
    def is_in_teamcity():
        return is_running_under_teamcity()

    def set_image_attachment(self, test_name, image_relative_path, name=None, flowId=None):
        self.message(
            'testMetadata',
            testName=test_name,
            name=name,
            type='image',
            value=image_relative_path,
            flowId=flowId
        )

    def print(self, message, status='NORMAL', flowId=None):
        if flowId is None:
            flowId = threading.get_ident()
        if self.is_in_teamcity():
            self.customMessage(message, status, flowId=str(flowId))
        else:
            print(message)
