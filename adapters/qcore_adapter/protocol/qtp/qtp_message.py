from qcore_adapter.protocol.exceptions import ProtocolException
from qcore_adapter.protocol.qtp.common import QTP_START, QTP_SIZE_MARKER, QTP_END
from qcore_adapter.protocol.qtp.qtp_decoder import QtpDecoder
import struct
from construct import Container, ListContainer


class QtpMessage(object):

    def __init__(self):
        self.bytes = bytearray()
        self._complete = False
        self._inner_message = None
        self._has_size = None
        self._size = None

    def is_complete(self):
        return self._complete

    def append_byte(self, byte: int):
        if self.is_complete():
            raise ProtocolException('Appending byte to a complete message')

        if len(self.bytes) == 0 and byte != QTP_START:
            raise ProtocolException(f'First byte is not start marker, {hex(byte)}')

        if len(self.bytes) == 1:
            if byte == QTP_SIZE_MARKER:
                self._has_size = True
            else:
                self._has_size = False

        self.bytes.append(byte)

        self.check_completion()

    def extend_bytes(self, bytes: bytearray):
        try:
            if len(self.bytes) > 4:
                self.bytes.extend(bytes)
                self.check_completion()
            else:
                for byte in bytes:
                    self.append_byte(byte)
        except Exception as e:
            print(f'Failed to parse {self.bytes}, {e}')
            raise ProtocolException()

    def check_completion(self):
        if len(self.bytes) == 4 and self._has_size:  # 0xbbdd_XXYY
            self._size = struct.unpack("<H", self.bytes[2:4])[0]

        if self._size is None:
            if self.bytes[-1] == QTP_END:
                self._complete = True
        else:  # has size

            if len(self.bytes) > self._size + 5:
                raise ProtocolException(f"Message size exceeded expected limit {self.bytes}")

            if len(self.bytes) == self._size + 5:  # bbddXXXX{...}cc
                self._complete = True

        if self._complete:
            if self.bytes[-1] != QTP_END:
                raise ProtocolException(f"Qtp last byte is not {self.bytes}")
            self._inner_message = QtpDecoder.decode(self._payload())

    def remaining_bytes(self):
        if self.is_complete():
            return 0

        if self._size is not None:
            return self._size + 5 - len(self.bytes)
        return 1

    def _payload(self):
        self.assert_completion()

        if self._has_size is False:
            return self.bytes[1:-1]
        else:
            return self.bytes[4:-1]

    def assert_completion(self):
        if not self.is_complete():
            raise ProtocolException("Message wasn't complete yet")

    @staticmethod
    def _search(container, compiled_pattern, search_all):
        items = []
        for key in container.keys():
            try:
                ret = []
                if isinstance(container[key], (Container, ListContainer)):
                    if isinstance(container[key], Container):
                        ret = QtpMessage._search(container[key], compiled_pattern, search_all)
                    else:
                        for list_item in container[key]:
                            ret.extend(QtpMessage._search(list_item, compiled_pattern, search_all))
                    if ret is not None and len(ret) > 0:
                        if search_all:
                            items.extend(ret)
                        else:
                            return ret
                if compiled_pattern == key:
                    if search_all:
                        items.append(container[key])
                    else:
                        return container[key]
            except Exception as e:
                pass
        if search_all:
            return items
        else:
            return None

    def get_field(self, field_name, is_unique=True):
        field = self._search(self.payload_root, field_name, True)
        if is_unique:
            assert len(field) == 1
            return field[0]
        return field

    def has_field(self, field_name):
        return len(self._search(self.payload_root, field_name, True)) > 0

    @property
    def payload_root(self) -> Container:
        self.assert_completion()

        return self._inner_message
