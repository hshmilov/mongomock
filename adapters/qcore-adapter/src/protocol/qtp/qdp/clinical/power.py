from construct import Struct, Enum, Byte, Int32ul

PowerSource = Enum(Byte, Battery=0, AC=1, Unknown=3)
PowerEvent = Enum(Byte, On=0, ToAC=1, ToBattery=2, ToSleep=3, Down=4, BatteryLevelChange=5, PowerChargeEvent=6)
ChargerStatus = Enum(Byte, Charging=0, OnBattery=1, ChargeError=3)
BatteryStatus = Enum(Byte, Good=0, Low=1, NoBattery=2, ReplaceBattery=3)
PowerState = Enum(Byte, On=0, Off=1, Sleep=2)

PowerClinicalStatus = Struct(
    'state' / PowerState,
    'event' / PowerEvent,
    'source' / PowerSource,
    'charger_status' / ChargerStatus,
    'battery_status' / BatteryStatus,
    'battery_voltage_level' / Byte,  # be it numbers...
    'total_time_on_battery_sec' / Int32ul,
    'total_time_in_service_sec' / Int32ul
)
