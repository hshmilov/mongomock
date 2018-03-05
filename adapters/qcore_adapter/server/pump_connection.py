from qcore_adapter.protocol.build_helpers.response_builder import get_registration_response_buffer
from qcore_adapter.protocol.consts import UNFINISHED_PARSING_MARKER
from qcore_adapter.protocol.exceptions import ProtocolException
from qcore_adapter.protocol.qtp.qtp_keepalive_message import QtpKeepAliveMessage
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage
import qcore_adapter.server.bins as bins

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

    def registration_flow(self, qtp: QtpMessage):

        # TODO: check if should register
        self._pump_state = PumpState(qtp, self._send_func)

        # send ack
        self._send_func(bins.ACK_ON_REGISTRATION)
        self._send_func(get_registration_response_buffer(pump_serial=self.pump_state.serial))
        self.is_registered = True

    def on_message(self, qtp: QtpMessage):

        if self.is_registered:
            self.pump_state.keepalive_mark()

        if isinstance(qtp.payload_root, QtpKeepAliveMessage):
            return

        print(f"Got {qtp.get_field('qdp_message_type')}")

        if qtp.has_field(UNFINISHED_PARSING_MARKER):
            print(f'Got partially parsed message = {qtp.bytes}')
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

        if self.is_registered is False:
            raise IOError('Reset connection, should register first')

        if qtp.has_field('LogDownloadResponseMessage'):
            # if self.is_registered:
            self.pump_state.handle_log_download(qtp)
            return

        if qtp.has_field('ClinicalStatus2Message'):
            # if self.is_registered:
            self.handle_clinical_message(qtp)
            return

        if qtp.get_field('qdp_message_type') == 'FileDeploymentInquiryRequest':
            print('Got file deployment, TBD later')
            return

        print(f'Got unknown qtp message:')
        print(qtp.bytes)
        print(qtp.payload_root)
