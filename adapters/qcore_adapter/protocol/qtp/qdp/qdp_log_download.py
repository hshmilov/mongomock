from construct import Struct, Pass, Int32ul, Byte, Enum, Embedded, If, this, GreedyRange, Probe, LazyBound, GreedyBytes

from qcore_adapter.protocol.qtp.common import QcoreInt64
from qcore_adapter.protocol.qtp.qdp.clinical_status2 import ClinicalStatus2Message

LOG_RTC_TIMESTAMP = 'rtc_timestamp'
LOG_SEQUENCE_ID = 'sequence_id'

LogMessageData = Struct(
    LOG_RTC_TIMESTAMP / Int32ul,
    LOG_SEQUENCE_ID / QcoreInt64
)

LogDownloadRequestMessage = Struct(
    'LogDownloadRequestMessage' / Pass,
    'report_start' / LogMessageData,
    'report_end' / LogMessageData,
    'tag' / Int32ul
)

LogDownloadBase = Struct(
    'response' / Enum(Byte, all_range=0, partial_range=1, cant_load=2, last=3),
    'report_start' / LogMessageData,
    'report_end' / LogMessageData,
    'tag' / Int32ul,
    'requested_from_sequence' / QcoreInt64,
    'requested_to_sequence' / QcoreInt64
)

SingleMsg = Struct(
    'has_msg' / Byte,
    Embedded(If(this.has_msg != 0, Embedded(Struct(
        'prot_ver' / Byte,
        'clinical_status2' / ClinicalStatus2Message
    ))))
)

LogDownloadResponseMessage = Struct(
    'LogDownloadResponseMessage' / Pass,
    Embedded(LogDownloadBase),
    'messages_list' / GreedyRange(SingleMsg)
)
