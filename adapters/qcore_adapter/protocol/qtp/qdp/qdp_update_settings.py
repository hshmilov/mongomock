from construct import Struct, Int32ul, Pass, this, Int32sl, Byte
from qcore_adapter.protocol.qtp.common import QcoreString

# TODO: Finish and send the update setting command
UpdateSettingsMessage = Struct(
    'UpdateSettingsRequest' / Pass,
    # 'protocol_version' / Byte,
    'infusion_update_period_sec' / Int32sl,
    'server_timezone' / QcoreString,
    'device_id' / QcoreString,
    'tag' / Int32sl
)
