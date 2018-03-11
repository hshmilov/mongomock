import time

from qcore_adapter.protocol.build_helpers import response_builder
from qcore_adapter.protocol.consts import PUMP_SERIAL, CLINICAL_STATUS
from qcore_adapter.protocol.qtp.qdp.clinical.sequence import CSI_SEQUENCE_NUMBER
from qcore_adapter.protocol.qtp.qdp.clinical_status2 import CSI_ITEM_TYPE, CSI_ITEM, CSI_ELEMENTS, CLINICAL_EVENT_TYPE, \
    ClinicalStatusItemType, ClinicalEvent
from qcore_adapter.protocol.qtp.qdp.qdp_message_types import QdpMessageTypes
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage
from qcore_adapter.qcore_mongo import QcoreMongo
from qcore_adapter.server.consts import KEEPALIVE_TS

HANDLED_MESSAGES = 'handled_messages'


class PumpState(object):
    def __init__(self, registration: QtpMessage, send_func):
        self.db = QcoreMongo()
        self.pump_info = registration.get_field('pump_info')
        self.serial = registration.get_field(PUMP_SERIAL)
        self.id = str(self.serial)
        self.pump_filter = {PUMP_SERIAL: self.id}
        self.table = self.db.table
        self.send_func = send_func

        self.update_db({PUMP_SERIAL: self.id, 'pump_info': self.pump_info})
        self.keepalive_mark()

        current_pump_state = self.table.find_one(filter=self.pump_filter) or dict()
        self.clinical_state = current_pump_state.get(CLINICAL_STATUS, dict())
        self.handled_messages = set(current_pump_state.get(HANDLED_MESSAGES, list()))
        self.last_request_missing_ts = time.time()
        self.start_record = 0
        self.end_record = 0
        self.handled_min = current_pump_state.get('handled_min', 0)

    def last_seen_pump(self):
        return self.table.find_one(filter=self.pump_filter)[KEEPALIVE_TS]

    def update_db(self, d):
        self.table.update_one(filter=self.pump_filter, update={"$set": d}, upsert=True)

    def keepalive_mark(self):
        self.update_db({KEEPALIVE_TS: time.time()})

    def request_missing(self, qtp: QtpMessage):
        self.last_request_missing_ts = time.time()

        clinical2 = self.extract_clinical_status(qtp)
        seq_id = clinical2['sequence_id']['low']
        self.start_record = max(self.start_record, clinical2['start_record']['low'])
        self.end_record = max(self.end_record, clinical2['end_record']['low'])
        self.on_sequence_number(seq_id)

        for seq in sorted(self.handled_messages):
            self.handled_min = seq
            self.handled_messages.discard(self.handled_min)
            if not self.handled_min + 1 in self.handled_messages:
                break

        missing_messages = sorted(range(max(self.handled_min + 1, self.start_record),
                                        min(*self.handled_messages, self.end_record, self.end_record)))

        print(f'missing messages {missing_messages}')
        for num in missing_messages:
            buff = response_builder.get_log_download_message(self.serial, 0, start={'high': 0, 'low': num},
                                                             end={'high': 0, 'low': num}, tag=num)
            self.send_func(buff)

        print(f'Updating handled messages last_handled={self.handled_min}, handled={sorted(self.handled_messages)}')
        self.update_db({HANDLED_MESSAGES: list(self.handled_messages),
                        'handled_min': self.handled_min})

    def update_clinical(self, qtp: QtpMessage):

        csi_elements = qtp.get_field(CSI_ELEMENTS)

        for element in csi_elements:
            csi_item = element[CSI_ITEM]
            item_type = element[CSI_ITEM_TYPE]

            # update state only if sequence number is greater
            if CSI_SEQUENCE_NUMBER in csi_item:
                stored_sequence = self.clinical_state.get(item_type, {}).get(CSI_SEQUENCE_NUMBER, 0)
                sequence_in_message = csi_item[CSI_SEQUENCE_NUMBER]
                self.on_sequence_number(sequence_in_message)

                if sequence_in_message > stored_sequence:
                    print(f'++++> Updating clinical entry {item_type} with recent data')
                    self.clinical_state[item_type] = csi_item

            else:
                self.clinical_state[item_type] = csi_item

        self._update_general_state(qtp)

        # store everything
        self.request_missing(qtp)
        self.update_db({CLINICAL_STATUS: self.clinical_state})

    def on_sequence_number(self, seq_id):
        if seq_id > self.handled_min:
            self.handled_messages.add(seq_id)

    def __del__(self):
        print('Connection to pump lost...')
        # a small hack, not necessary but allows to discover disconnect faster
        self.update_db({KEEPALIVE_TS: 0.0})

    def extract_clinical_status(self, qtp: QtpMessage):
        if qtp.get_field('qdp_message_type') == QdpMessageTypes.LogDownloadResponse.name:
            return qtp.get_field('clinical_status2')
        else:
            return qtp.get_field('qdp_payload')

    def _update_general_state(self, qtp):
        clinical2_state = self.extract_clinical_status(qtp)
        sequence_in_message = clinical2_state['sequence_id']['low']

        self.on_sequence_number(sequence_in_message)

        stored_sequence = self.clinical_state.get('general', {}).get('sequence_id', {}).get('low', 0)

        if sequence_in_message > stored_sequence:
            self.clinical_state['general'] = clinical2_state
            del self.clinical_state['general'][CSI_ELEMENTS]
            del self.clinical_state['general']['items_list_size']

    def handle_log_download(self, qtp: QtpMessage):

        seq_id = qtp.get_field('report_start')['sequence_id']['low']
        print(f'Got log download with seq {seq_id}')
        self.on_sequence_number(seq_id)

        if qtp.has_field('ClinicalStatus2Message'):
            self.update_clinical(qtp)
