from construct import Struct, Byte, Int32ul, Switch, OneOf, Pass, this, Enum, Const, GreedyRange

from protocol.consts import PUMP_SERIAL
from protocol.qtp.qdp.clinical_status2 import ClinicalStatus2Message
from protocol.qtp.qdp.qdp_file_deployment import FileDeploymentInquiryRequestMessage
from protocol.qtp.qdp.qdp_message_types import QdpMessageTypes, QdpMessageTypesReverseMapping
from protocol.qtp.qdp.qdp_registration import RegistrationRequestMessage, RegistrationResponseMessage
from protocol.qtp.qdp.qdp_time_sync import TimeSyncMessage

QDP_MESSAGE_START_MARK = 0x9c
SUPPORTED_PROTOCOL_VERSION = 0x91  # 1.45

QdpHeader = Struct(
    'QdpHeader' / Pass,
    'qdp_message_type' / Enum(Byte, **QdpMessageTypesReverseMapping),
    PUMP_SERIAL / Int32ul,
    'start_mark' / Const(QDP_MESSAGE_START_MARK, Byte),
    'protocol_version' / Byte,  # validate protocol for most of the messages except connection ConnectionEstablished
    'qdp_payload' / Switch(this.qdp_message_type, {
        QdpMessageTypes.RegistrationMessage.name: RegistrationRequestMessage,
        QdpMessageTypes.RegistrationResponse.name: RegistrationResponseMessage,
        QdpMessageTypes.TimeSync.name: TimeSyncMessage,
        QdpMessageTypes.ConnectionEstablished.name: Struct(
            'ConnectionEstablishedMessage' / Pass
        ),
        QdpMessageTypes.ClinicalStatusConnectivityUpdate.name: ClinicalStatus2Message,
        QdpMessageTypes.FileDeploymentInquiryRequest.name: FileDeploymentInquiryRequestMessage
    }, default=Struct(
        'UNHANDLED_QDP_TYPE' / Pass,
        'TODO' / GreedyRange(Byte)
    )),
)
