import dpkt
import ipaddress

from pathlib import Path

from qcore_adapter.protocol.exceptions import ProtocolException
from qcore_adapter.protocol.qtp.qtp_keepalive_message import QtpKeepAliveMessage
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage

import construct

construct.setglobalfullprinting(True)


def bytes_to_ip(bytes):
    return str(ipaddress.ip_address(bytes))


path = Path(__file__).parent / 'caps' / 'dl2.pcap'

streams = dict()

f = open(path, "rb")
pcap = dpkt.pcap.Reader(f)
first_ts = None
for ts, buff in pcap:

    if first_ts is None:
        first_ts = ts

    current_ts = ts
    pk = dpkt.ethernet.Ethernet(buff)
    ip = pk.ip
    tcp = ip.tcp
    if 5100 not in [tcp.sport, tcp.dport]:
        continue
    stream_name = f"{bytes_to_ip(ip.src)}:{ip.tcp.sport}=>{bytes_to_ip(ip.dst)}:{ip.tcp.dport}"
    tcp_payload = pk.ip.tcp.data
    stream = streams.setdefault(stream_name, [QtpMessage()])
    last_msg = stream[-1]

    for byte in tcp_payload:

        # try:
        last_msg.append_byte(byte)
        if last_msg.is_complete():
            # if ip.tcp.sport == 5100:
            print(f'TIME={round(ts-first_ts,2)} # flow={stream_name}')
            # print(last_msg.bytes.hex().find('09030000'))
            print(last_msg.bytes)
            print(last_msg.payload_root)
            print("<==============================>")
            last_msg = QtpMessage()
            stream.append(last_msg)
    # except ProtocolException as e:
    #     last_msg = QtpMessage()
    #     stream.append(last_msg)
    #     print(e)

#     if last_msg.is_complete():
#         print(last_msg.payload_root)
#         last_msg = QtpMessage()
#         stream.append(last_msg)
#     last_msg.extend_bytes(tcp_payload)
#
# for sid, stream in streams.items():
#     print(f'Stream {sid} {stream["ts"]} {stream["data"]}')
#     qtp = QtpMessage()
#
#     # try:
#     #     for bt in data:
#     #         qtp.append_byte(bt)
#     #         if qtp.is_complete():
#     #
#     #             if not isinstance(qtp.payload_root, QtpKeepAliveMessage) and not qtp.has_field('QcaHeader'):
#     #                 print(qtp.payload_root)
#     #                 print('================================')
#     #                 print()
#     #
#     #             qtp = QtpMessage()
#     # except ProtocolException as e:
#     #     print("Error:", e)
