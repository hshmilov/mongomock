from construct import Struct, Byte, Int32ul, Switch, OneOf, Pass, this, Enum, Const, GreedyRange, Check, len_, Optional, \
    Default, Probe

from qcore_adapter.protocol.consts import PUMP_SERIAL, UNFINISHED_PARSING_MARKER
from qcore_adapter.protocol.qtp.qdp.clinical_status2 import ClinicalStatus2Message
from qcore_adapter.protocol.qtp.qdp.qdp_device_notify import DeviceNotifyMessage
from qcore_adapter.protocol.qtp.qdp.qdp_file_deployment_inquiry_request import FileDeploymentInquiryRequestMessage
from qcore_adapter.protocol.qtp.qdp.qdp_log_download import LogDownloadRequestMessage, LogDownloadResponseMessage
from qcore_adapter.protocol.qtp.qdp.qdp_message_types import QdpMessageTypes, QdpMessageTypesReverseMapping
from qcore_adapter.protocol.qtp.qdp.qdp_package_deploy_request import PackageDeployRequestMessage
from qcore_adapter.protocol.qtp.qdp.qdp_registration import RegistrationRequestMessage, RegistrationResponseMessage
from qcore_adapter.protocol.qtp.qdp.qdp_time_sync import TimeSyncMessage
from qcore_adapter.protocol.qtp.qdp.qdp_update_settings import UpdateSettingsRequestMessage

QDP_MESSAGE_START_MARK = 0x9c

QdpHeader = Struct(
    'QdpHeader' / Pass,
    'qdp_message_type' / Enum(Byte, **QdpMessageTypesReverseMapping),
    PUMP_SERIAL / Int32ul,
    'start_mark' / Const(QDP_MESSAGE_START_MARK, Byte),

    'protocol_version' / Byte,  # validate protocol for most of the messages except connection ConnectionEstablished
    #  from Shared/Mednet/QdpMessageFactory.cpp
    'qdp_payload' / Switch(this.qdp_message_type, {
        QdpMessageTypes.RegistrationMessage.name: RegistrationRequestMessage,
        QdpMessageTypes.RegistrationResponse.name: RegistrationResponseMessage,
        QdpMessageTypes.TimeSync.name: TimeSyncMessage,
        QdpMessageTypes.FileDeploymentInquiryRequest.name: FileDeploymentInquiryRequestMessage,
        QdpMessageTypes.DeviceNotify.name: DeviceNotifyMessage,
        QdpMessageTypes.DeviceUpdate.name: UpdateSettingsRequestMessage,
        QdpMessageTypes.FileDeploymentRequest.name: PackageDeployRequestMessage,

        QdpMessageTypes.ConnectionEstablished.name: Struct(
            'ConnectionEstablishedMessage' / Pass,
            'not interesting' / GreedyRange(Byte)
        ),

        # clinical status
        QdpMessageTypes.ClinicalStatusConnectivityUpdate.name: ClinicalStatus2Message,
        QdpMessageTypes.ClinicalStatusAlarmUpdate_woInfusion.name: ClinicalStatus2Message,
        QdpMessageTypes.ClinicalStatusInfusionUpdate.name: ClinicalStatus2Message,
        QdpMessageTypes.ClinicalStatusRulesetViolationUpdate.name: ClinicalStatus2Message,
        QdpMessageTypes.ClinicalStatusPowerUpdate.name: ClinicalStatus2Message,
        QdpMessageTypes.ClinicalStatusCommandResponseUpdate.name: ClinicalStatus2Message,
        QdpMessageTypes.ClinicalStatusAlarmUpdate_wInfusion.name: ClinicalStatus2Message,
        QdpMessageTypes.ClinicalStatusSystemUpdate.name: ClinicalStatus2Message,
        QdpMessageTypes.ClinicalStatusCcaUpdate.name: ClinicalStatus2Message,

        # log
        QdpMessageTypes.LogDownloadRequest.name: LogDownloadRequestMessage,
        QdpMessageTypes.LogDownloadResponse.name: LogDownloadResponseMessage,

    }, default=Struct(
        UNFINISHED_PARSING_MARKER / Pass,
        'TODO' / GreedyRange(Byte)
    )),
    'leftovers' / Default(GreedyRange(Byte), b''),
    Check(len_(this.leftovers) == 0)
)
