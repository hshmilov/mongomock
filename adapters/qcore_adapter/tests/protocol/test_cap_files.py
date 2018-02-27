import dpkt
import ipaddress

from pathlib import Path

from qcore_adapter.protocol.exceptions import ProtocolException
from qcore_adapter.protocol.qtp.qtp_keepalive_message import QtpKeepAliveMessage
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage


def bytes_to_ip(bytes):
    return str(ipaddress.ip_address(bytes))


path = Path(__file__).parent / 'caps' / 'SimpleInfusion.pcap'

streams = dict()

f = open(path, "rb")
pcap = dpkt.pcap.Reader(f)
for ts, buff in pcap:
    pk = dpkt.ethernet.Ethernet(buff)
    ip = pk.ip
    tcp = ip.tcp
    if 5100 not in [tcp.sport, tcp.dport]:
        continue
    stream_name = f"{bytes_to_ip(ip.src)}:{tcp.sport}<->{bytes_to_ip(ip.dst)}:{tcp.dport}"
    tcp_payload = pk.ip.tcp.data
    stream = streams.setdefault(stream_name, b'')
    stream += tcp_payload
    streams[stream_name] = stream

for sid, data in streams.items():

    print("Stream, ", sid, " ", data)
    qtp = QtpMessage()

    try:
        for bt in data:
            qtp.append_byte(bt)
            if qtp.is_complete():

                if not isinstance(qtp.payload_root, QtpKeepAliveMessage) and not qtp.has_field('QcaHeader'):
                    print(qtp.payload_root)
                    print('================================')
                    print()

                qtp = QtpMessage()
    except ProtocolException as e:
        print("Error:", e)
