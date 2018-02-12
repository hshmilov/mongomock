from construct import Struct, Enum, Byte, Int32ul, Embedded

from protocol.qtp.qdp.clinical.sequence import QcoreSequence

KeypadLockout = Enum(Byte, Unlocked=0, SoftLockout=1, HardLockout=2)
InfuserState = Enum(Byte, Ready=0, On=1, Alarming=2, Sleep=3, Off=4, DrugLibrary=5, Software=6, LanguageFile=7,
                    Priming=8)

InfuserClinicalStatus = Struct(
    Embedded(QcoreSequence),
    'infuser_state' / InfuserState,
    'keypad_lockout' / KeypadLockout
)
