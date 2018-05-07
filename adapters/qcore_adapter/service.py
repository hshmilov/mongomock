import logging
logger = logging.getLogger(f"axonius.{__name__}")
from datetime import timedelta
from threading import Thread

import time

from axonius.adapter_base import AdapterBase
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from qcore_adapter.protocol.build_helpers.construct_dict import dict_filter
from qcore_adapter.protocol.consts import PUMP_SERIAL, CLINICAL_STATUS
from qcore_adapter.protocol.qtp.qdp.clinical.sequence import CSI_SEQUENCE_NUMBER
from qcore_adapter.protocol.qtp.qdp.clinical_status2 import ClinicalStatusItemType
from qcore_adapter.qcore_mongo import QcoreMongo
from qcore_adapter.server.consts import KEEPALIVE_TS
from qcore_adapter.server.mediator_server import run_mediator_server

APERIODIC = ClinicalStatusItemType.Aperiodic_Infusion.name
PERIODIC = ClinicalStatusItemType.Infusion.name


class QcoreAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pump_serial = Field(str, 'pump serial number')
        connection_status = Field(str, 'connection status')
        pump_name = Field(str, 'pump name')
        sw_version = Field(str, 'sw version')
        dl_version = Field(str, 'dl version')
        location = Field(str, 'location')

        # Taken from periodic/aperiodic message updates
        inf_time_remaining = Field(str, 'Time remaining')
        inf_volume_remaining = Field(str, 'Volume remaining [ml]')
        inf_volume_infused = Field(str, 'Volume infused [ml]')
        inf_line_id = Field(int, 'Line id')
        inf_total_bag_volume_delivered = Field(float, 'Total bag volume delivered [ml]')  # complex
        inf_is_bolus = Field(bool, 'Is Bolus')  # complex
        inf_bolus_data = Field(list, 'Bolus data')  # complex

        # taken from aperiodic only
        inf_medication = Field(str, 'Medication')
        inf_cca = Field(int, 'Cca index')
        inf_delivery_rate = Field(float, 'Infusion rate [ml/h]')

        inf_infusion_event = Field(str, 'Infusion event')  # complex
        inf_dose_rate = Field(float, 'Dose rate')  # complex
        inf_dose_rate_units = Field(str, 'Units')  # complex
        inf_status = Field(list, 'Infusion status')  # complex

        gen_device_context_type = Field(str, 'Context type')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

        # add one client ...
        if self._get_collection('clients').count({}) == 0:
            self._add_client({'mediator': '1'})

        self.thread = Thread(target=run_mediator_server)
        self.thread.start()

    def _connect_client(self, client_config):
        return {'mediator': '1'}

    def populate_nic(self, device, pump_document):
        try:
            connectivity = pump_document[CLINICAL_STATUS]['Connectivity']
            mac = connectivity['mac']
            ip = connectivity['ip_address']
            device.add_nic(mac=mac, ips=[ip])
        except Exception:
            logger.exception(f"failed to populate nic info")

    def populate_infusion_status(self, device, pump_document):
        try:
            clinical_status = pump_document[CLINICAL_STATUS]

            aperiodic_inf_state = None

            if APERIODIC in clinical_status:
                aperiodic_status = clinical_status[APERIODIC]

                device.inf_medication = aperiodic_status['external_drug_id']
                device.inf_cca = aperiodic_status['cca_index']
                device.inf_delivery_rate = aperiodic_status['delivery_infusion_rate']

                device.inf_dose_rate = aperiodic_status['dose_rate']
                device.inf_dose_rate_units = aperiodic_status['rate_units_parsed']

                device.inf_status = [k for k, v in aperiodic_status['operational_status'].items() if v is True]

                device.inf_infusion_event = aperiodic_status['infusion_event']

                # this data exists both in periodic and aperiodic and we will take the most recent
                aperiodic_inf_state = aperiodic_status['csi_infusion_state']

                self.populate_infusion_state(device, aperiodic_inf_state)

            if PERIODIC in clinical_status:
                periodic_status = clinical_status[PERIODIC]

                if aperiodic_inf_state is None \
                        or periodic_status[CSI_SEQUENCE_NUMBER] > aperiodic_inf_state[CSI_SEQUENCE_NUMBER]:
                    self.populate_infusion_state(device, periodic_status)

        except Exception:
            logger.exception("Failed to populate infusion status")

    def populate_infusion_state(self, device, infusion):
        device.inf_is_bolus = infusion['is_bolus'] != 0
        if device.inf_is_bolus != 0:
            device.inf_bolus_data = [f'{k}:{round(v,3)}' for k, v in infusion['bolus_data'].items()]
            device.inf_time_remaining = 'N/A'
            device.inf_volume_remaining = 'N/A'
            device.inf_volume_infused = 'N/A'
        else:
            device.inf_bolus_data = ['N/A']
            device.inf_time_remaining = str(timedelta(seconds=infusion['total_time_remaining']))
            device.inf_volume_remaining = str(infusion['total_volume_remaining'] / 1000.)
            device.inf_volume_infused = str(infusion['total_volume_delivered'] / 1000.)

        device.inf_line_id = infusion['line_id']
        device.inf_total_bag_volume_delivered = infusion['total_bag_volume_delivered'] / 1000.

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

            self.populate_infusion_status(device, pump_document)

            device.set_raw(pump_document)
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
