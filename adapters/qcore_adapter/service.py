import logging
logger = logging.getLogger(f'axonius.{__name__}')
from datetime import timedelta
from threading import Thread
from collections import defaultdict

import time

from axonius.adapter_base import AdapterBase
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from qcore_adapter.protocol.build_helpers.construct_dict import dict_filter
from qcore_adapter.protocol.consts import PUMP_SERIAL, CLINICAL_STATUS, INFUSIONS
from qcore_adapter.protocol.qtp.qdp.clinical.sequence import CSI_SEQUENCE_NUMBER
from qcore_adapter.protocol.qtp.qdp.clinical_status2 import ClinicalStatusItemType
from qcore_adapter.qcore_mongo import QcoreMongo
from qcore_adapter.server.consts import KEEPALIVE_TS
from qcore_adapter.server.mediator_server import run_mediator_server
from qcore_adapter.server.pump_state import DISCONNECTS


def merge_dicts(list_of_dicts):
    dict3 = defaultdict(list)
    for d in list_of_dicts:
        for k, v in d.items():
            dict3[k].append(v)
    return dict3


class QcoreAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pump_serial = Field(str, 'pump serial number')
        connection_status = Field(str, 'connection status')
        pump_name = Field(str, 'pump name')
        sw_version = Field(str, 'sw version')
        dl_version = Field(str, 'dl version')
        location = Field(str, 'location')

        inf_time_remaining = ListField(str, 'Time remaining')
        inf_volume_remaining = ListField(float, 'Volume remaining [ml]')
        inf_volume_infused = ListField(float, 'Volume infused [ml]')
        inf_line_id = ListField(int, 'Line id')
        inf_is_bolus = ListField(int, 'Is Bolus')
        inf_bolus_data = ListField(str, 'Bolus data')

        inf_medication = ListField(str, 'Medication')
        inf_cca = ListField(int, 'Cca index')
        inf_delivery_rate = ListField(float, 'Infusion rate [ml/h]')

        inf_infusion_event = ListField(str, 'Infusion event')
        inf_dose_rate = ListField(float, 'Dose rate')
        inf_dose_rate_units = ListField(str, 'Units')
        inf_status = ListField(list, 'Infusion status')

        inf_total_bag_volume_delivered = ListField(float, 'Total bag vol delivered [ml]')

        gen_device_context_type = Field(str, 'Context type')
        alarm = Field(str, 'Alarm code')
        disconnects = Field(int, 'Disconnects')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

        # add one client ...
        if self._clients_collection.count_documents({}) == 0:
            self._add_client({'mediator': '1'})

        self.thread = Thread(target=run_mediator_server)
        self.thread.start()
        self.last_alarm = None

    def _connect_client(self, client_config):
        return {'mediator': '1'}

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def populate_nic(self, device, pump_document):
        try:
            connectivity = pump_document[CLINICAL_STATUS]['Connectivity']
            mac = connectivity['mac']
            ip = connectivity['ip_address']
            device.add_nic(mac=mac, ips=[ip])
        except Exception:
            logger.exception(f"failed to populate nic info")

    def raise_alarm_notification(self, device, pump_document):
        try:
            clinical_status = pump_document[CLINICAL_STATUS]
            if 'Alarm' not in clinical_status:
                return
            current_alarm = clinical_status['Alarm']['code']
            device.alarm = current_alarm
            if self.last_alarm is None:
                self.last_alarm = current_alarm
            else:
                if self.last_alarm != current_alarm:
                    self.last_alarm = current_alarm
                    self.logger.info('Generating alarm notification')
                    self.create_notification(
                        title=f'Pump\'s {device.pump_name} current alarm changed to {current_alarm}',
                        content=f'Pump\'s {device.pump_name} current alarm changed to {current_alarm}')
        except Exception as e:
            self.logger.error(f'Failed to populate Alarm {e}')

    def populate_clinical_status(self, device, pump_document):
        try:
            clinical_status = pump_document[CLINICAL_STATUS]

            if INFUSIONS not in clinical_status:
                return

            merged = merge_dicts(clinical_status[INFUSIONS].values())

            device.inf_medication = merged['external_drug_id']
            device.inf_cca = merged['cca_index']
            device.inf_delivery_rate = merged['delivery_infusion_rate']

            device.inf_dose_rate = merged['dose_rate']
            device.inf_dose_rate_units = merged['rate_units_parsed']

            def repr_inf_status(infst):
                return [k for k, v in infst.items() if v is True]

            device.inf_status = [repr_inf_status(infst) for infst in merged['operational_status']]
            device.inf_infusion_event = merged['infusion_event']

            self.populate_infusion_state(device, merged)
        except Exception:
            logger.exception("Failed to populate infusion status")

    def populate_infusion_state(self, device, merged):
        device.inf_is_bolus = merged['is_bolus']
        device.inf_bolus_data = [str(bd) for bd in merged['bolus_data']]

        device.inf_time_remaining = [str(timedelta(seconds=ttr)) for ttr in merged['total_time_remaining']]
        device.inf_volume_remaining = [vr / 1000. for vr in merged['total_volume_remaining']]
        device.inf_volume_infused = [vi / 1000. for vi in merged['total_volume_delivered']]

        device.inf_line_id = merged['line_id']
        device.inf_total_bag_volume_delivered = [tbag / 1000. for tbag in merged['total_bag_volume_delivered']]

    def _query_devices_by_client(self, client_name, client_data):
        qcore_mongo = QcoreMongo()
        return list(qcore_mongo.all_pumps)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "mediator",
                    "title": "Qcore mediator",
                    "type": "string"
                }
            ],
            "required": [
                "mediator"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        now = time.time()

        for pump_document in devices_raw_data:
            device = self._new_device_adapter()
            device.id = pump_document[PUMP_SERIAL]
            device.connection_status = 'online' if now - pump_document[KEEPALIVE_TS] < 60 else 'offline'
            self.populate_nic(device, pump_document)

            pump_info = pump_document['pump_info']
            infuser_info = pump_info['infuser_info']

            device.pump_serial = device.id
            device.pump_name = infuser_info['infuser_name']

            device.sw_version = infuser_info['active_infuser_sw']['version']
            device.dl_version = infuser_info['active_dl']['name']

            if CLINICAL_STATUS in pump_document:
                device.location = pump_document[CLINICAL_STATUS]['Connectivity']['bssid']
                device.gen_device_context_type = pump_document[CLINICAL_STATUS].get('general', {}).get(
                    'device_context_type', '')

            self.populate_clinical_status(device, pump_document)

            device.set_raw(pump_document)
            device.disconnects = pump_document.get(DISCONNECTS, 0)

            self.raise_alarm_notification(device, pump_document)

            logger.info(f'Yielding a device: ')
            for k, v in device.to_dict().items():
                if str(k).startswith("inf_"):
                    logger.info(f'{k}:{v}')

            yield device

    def _get_client_id(self, client_config):
        return client_config['mediator']

    @classmethod
    def adapter_properties(cls):
        return []
