from qcore_adapter.protocol.build_helpers import response_builder
from qcore_adapter.protocol.build_helpers.response_builder import get_registration_response_buffer, \
    get_update_settings_buffer
from qcore_adapter.protocol.consts import UNFINISHED_PARSING_MARKER
from qcore_adapter.protocol.exceptions import ProtocolException
from qcore_adapter.protocol.qtp.qtp_keepalive_message import QtpKeepAliveMessage
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage
import qcore_adapter.server.bins as bins
from qcore_adapter.server.consts import dl_flow_packets

from qcore_adapter.server.pump_state import PumpState


class PumpConnection(object):
    def __init__(self, send_func):
        self._send_func = send_func
        self.is_registered = False
        self._pump_state = None

        print('Sending Connection established')
        self._send_func(bins.CONNECTION_ESTABLISHED)

    @property
    def pump_state(self) -> PumpState:
        return self._pump_state

    def handle_clinical_message(self, qtp: QtpMessage):
        self.pump_state.update_clinical(qtp)

    def update_flow(self):

        for msg_bytes in dl_flow_packets:
            import time
            time.sleep(0.8)
            bytes_to_send = response_builder.replace_serial_and_wrap(msg_bytes, self.pump_state.serial)
            m = QtpMessage()
            m.extend_bytes(bytes_to_send)
            print(f'<<<<================================== Sending as part of DL update flow')
            print(m.bytes)
            print(m.payload_root)
            self._send_func(bytes_to_send)
            print(f'=====================================')

    def registration_flow(self, qtp: QtpMessage):

        self._pump_state = PumpState(qtp, self._send_func)

        # send ack
        self._send_func(bins.ACK_ON_REGISTRATION)
        self._send_func(get_registration_response_buffer(pump_serial=self.pump_state.serial))
        self.is_registered = True

        # send update settings
        self._send_func(get_update_settings_buffer(self.pump_state.serial, 30))

        # go to update!
        # self.update_flow()

    def on_message(self, qtp: QtpMessage):

        if self.is_registered:
            self.pump_state.keepalive_mark()

        if isinstance(qtp.payload_root, QtpKeepAliveMessage):
            return

        print(f'Parsed qtp message:')
        print(qtp.bytes)
        print(qtp.payload_root)

        if qtp.has_field(UNFINISHED_PARSING_MARKER):
            print(f'>>>>>>>>>>>>>>>>>>>>>>>>>==== Got partially parsed message = {qtp.bytes}')
            print(qtp.payload_root)

        if qtp.has_field('EmptyMessage'):
            print('Got keepalive')
            return

        if qtp.has_field('TimeSyncMessage'):
            print('Got TimeSyncMessage')
            self._send_func(bins.TIMESYNC_ACK)
            self._send_func(bins.HARDCODED_TIMESYNC)
            return

        if qtp.has_field('RegistrationRequestMessage'):
            print('Entering registration flow')
            self.registration_flow(qtp)
            return

        # Only register message from here on

        # if self.is_registered is False:
        #     raise ProtocolException('Reset connection, should register first')

        if qtp.has_field('LogDownloadResponseMessage'):
            self.pump_state.handle_log_download(qtp)
            return

        if qtp.has_field('ClinicalStatus2Message'):
            self.handle_clinical_message(qtp)
            return
