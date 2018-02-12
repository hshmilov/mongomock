#!/usr/bin/env python3
from protocol.qtp.qtp_decoder import QtpDecoder
from protocol.qtp.qtp_message import QtpMessage
import sys

if __name__ == '__main__':
    packet = sys.argv[1]
    qtp = QtpMessage()
    buff = bytearray.fromhex(packet)
    qtp.extend_bytes(buff)
    print(qtp.payload_root)
