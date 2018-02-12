from protocol.build_helpers.registration import get_registration_response_buffer
from protocol.consts import PUMP_SERIAL
from protocol.qtp.qtp_keepalive_message import QtpKeepAliveMessage
from protocol.qtp.qtp_message import QtpMessage
import qcore_server.bins as bins

from qcore_mongo import QcoreMongo


class PumpState(object):
    def __init__(self, registration: QtpMessage):
        self.db = QcoreMongo()
        self.pump_info = registration.get_field('pump_info')
        self.serial = registration.get_field(PUMP_SERIAL)
        self.id = str(self.serial)
        self.clinical_state = {}
        self.pump_filter = {PUMP_SERIAL: self.id}
        self.table = self.db.table
        self.table.update_one(filter=self.pump_filter,
                              update={
                                  "$set": {'pump_info': self.pump_info, 'status': 'ONLINE', PUMP_SERIAL: self.id}},
                              upsert=True)

    def update_clinical(self, qtp: QtpMessage):
        csi_elements = qtp.get_field('csi_elements')
        for element in csi_elements:
            # TODO: insert only newer ts (if has sequence number...)
            self.clinical_state[element['csi_item_type']] = element['csi_item']

        print("Clinical state")
        for k, v in self.clinical_state.items():
            print(k, v)
            self.table.update_one(filter=self.pump_filter,
                                  update={"$set": {'clinical_status': self.clinical_state}}, upsert=True)

    def __del__(self):
        # TODO: use contextlib ...
        print("Connection to pump lost...")
        self.table.update_one(filter=self.pump_filter, update={"$set": {'status': 'OFFLINE'}}, upsert=True)


class PumpConnection(object):
    def __init__(self, send_func):
        self._send_func = send_func
        self.is_registered = False
        self._registered_pumps = dict()
        self._pump_state = None

        print("Sending Connection established")
        self._send_func(bins.CONNECTION_ESTABLISHED)

    @property
    def pump_state(self) -> PumpState:
        return self._pump_state

    def handle_clinical_message(self, qtp: QtpMessage):
        self.pump_state.update_clinical(qtp)

    def registration_flow(self, qtp: QtpMessage):

        # TODO: check if should register
        self._pump_state = PumpState(qtp)

        # send ack
        self._send_func(bins.ACK_ON_REGISTRATION)
        self._send_func(get_registration_response_buffer(pump_serial=self.pump_state.serial))
        self.is_registered = True

    def on_message(self, qtp: QtpMessage):

        if isinstance(qtp.payload_root, QtpKeepAliveMessage):
            return

        if qtp.has_field('EmptyMessage'):
            print("Got keepalive")
            return

        if qtp.has_field('TimeSyncMessage'):
            print("Got TimeSyncMessage")
            self._send_func(bins.TIMESYNC_ACK)
            self._send_func(bins.HARDCODED_TIMESYNC)
            return

        if qtp.has_field('RegistrationRequestMessage'):
            print('Entering registration flow')
            self.registration_flow(qtp)
            return

        if qtp.has_field('ClinicalStatus2Message'):
            self.handle_clinical_message(qtp)
            return

        if qtp.has_field('UNHANDLED_QDP_TYPE'):
            print(f'unknown message = {qtp.bytes}')
            print(qtp.payload_root)
            return

        print(qtp.payload_root)
