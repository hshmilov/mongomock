import time

from qcore_adapter.protocol.consts import PUMP_SERIAL, CLINICAL_STATUS
from qcore_adapter.protocol.qtp.qdp.clinical.sequence import CSI_SEQUENCE_NUMBER
from qcore_adapter.protocol.qtp.qdp.clinical_status2 import CSI_ITEM_TYPE, CSI_ITEM, CSI_ELEMENTS, CLINICAL_EVENT_TYPE
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage
from qcore_adapter.qcore_mongo import QcoreMongo
from qcore_adapter.server.consts import KEEPALIVE_TS


class PumpState(object):
    def __init__(self, registration: QtpMessage):
        self.db = QcoreMongo()
        self.pump_info = registration.get_field('pump_info')
        self.serial = registration.get_field(PUMP_SERIAL)
        self.id = str(self.serial)
        self.pump_filter = {PUMP_SERIAL: self.id}
        self.table = self.db.table

        self.update_db({PUMP_SERIAL: self.id, 'pump_info': self.pump_info})
        self.keepalive_mark()

        current_pump_state = self.table.find_one(filter=self.pump_filter) or dict()
        self.clinical_state = current_pump_state.get(CLINICAL_STATUS, dict())

    def last_seen_pump(self):
        return self.table.find_one(filter=self.pump_filter)[KEEPALIVE_TS]

    def update_db(self, d):
        self.table.update_one(filter=self.pump_filter, update={"$set": d}, upsert=True)

    def keepalive_mark(self):
        self.update_db({KEEPALIVE_TS: time.time()})

    def update_clinical(self, qtp: QtpMessage):
        csi_elements = qtp.get_field(CSI_ELEMENTS)

        if qtp.has_field(CLINICAL_EVENT_TYPE):
            print(f'==================> Got {qtp.get_field(CLINICAL_EVENT_TYPE)}')

        for element in csi_elements:
            csi_item = element[CSI_ITEM]
            item_type = element[CSI_ITEM_TYPE]

            if 'Aperiodic_Infusion' in item_type:
                print(f'{item_type}:{csi_item}')

            self.clinical_state[item_type] = csi_item

            # update state only if sequence number is greater
            if CSI_SEQUENCE_NUMBER in csi_item:
                stored_sequence = self.clinical_state.get(item_type, {}).get(CSI_SEQUENCE_NUMBER, 0)
                if csi_item[CSI_SEQUENCE_NUMBER] > stored_sequence:
                    print(f'++++> Updating clinical entry {item_type} with recent data')
                    self.clinical_state[item_type] = csi_item
                else:
                    print(f'----> {item_type} was stale, discarding')
            else:
                self.clinical_state[item_type] = csi_item

        self._update_general_state(qtp)

        # store everything
        self.update_db({CLINICAL_STATUS: self.clinical_state})

    def __del__(self):
        print('Connection to pump lost...')
        # a small hack, not necessary but allows to discover disconnect faster
        self.update_db({KEEPALIVE_TS: 0.0})

    def _update_general_state(self, qtp):
        clinical2_state = qtp.get_field('qdp_payload')
        sequence_in_message = clinical2_state['sequence_id']['low']
        stored_sequence = self.clinical_state.get('general', {}).get('sequence_id', {}).get('low', 0)

        if sequence_in_message > stored_sequence:
            self.clinical_state['general'] = clinical2_state
            del self.clinical_state['general'][CSI_ELEMENTS]
            del self.clinical_state['general']['items_list_size']
