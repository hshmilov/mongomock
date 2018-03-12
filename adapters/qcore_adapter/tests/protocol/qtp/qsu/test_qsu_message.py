import pytest

from qcore_adapter.protocol.qtp.qtp_message import QtpMessage


class TestQsu(object):

    def test_file_write_data_request(self):
        buff = bytearray(
            b'\xbb\xdd\xa9\x04\xca\x02\t\x03\x00\x00\x00\x00\x00\x00\x0ef0\x1d\xe7\x96\x97\x04\x00\x9d\xb9\x03\x8f\x04\x00\x00HTTP/1.1 416 Requested Range Not Satisfiable\r\nX-Frame-Options: SAMEORIGIN\r\nContent-Range: bytes */105033\r\nContent-Type: text/html;charset=utf-8\r\nContent-Length: 951\r\nDate: Wed, 07 Mar 2018 13:46:33 GMT\r\nServer:  \r\n\r\n<html><head><title>JBossWeb/2.0.1.GA - Error report</title><style><!--H1 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:22px;} H2 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:16px;} H3 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:14px;} BODY {font-family:Tahoma,Arial,sans-serif;color:black;background-color:white;} B {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;} P {font-family:Tahoma,Arial,sans-serif;background:white;color:black;font-size:12px;}A {color : black;}A.name {color : black;}HR {color : #525D76;}--></style> </head><body><h1>HTTP Status 416 - </h1><HR size="1" noshade="noshade"><p><b>type</b> Status report</p><p><b>message</b> <u></u></p><p><b>description</b> <u>The requested byte range cannot be satisfied ().</u></p><HR size="1" noshade="noshade"><h3>JBossWeb/2.0.1.GA</h3></body></html>\xcc')
        qtp = QtpMessage()
        qtp.extend_bytes(bytes=buff)
        assert qtp.get_field('data_size') == 1167

    def test_file_write_response(self):
        buff = bytearray(
            b'\xbb\xdd\x1b\x00\xca\t\t\x03\x00\x00\x00\x00\x00\x00\x15f\x8e5@\xa0\t\x00\x00\x00\x9d\xb9\x03\x8f\x04\x00\x00\xcc')
        qtp = QtpMessage()
        qtp.extend_bytes(bytes=buff)
        assert qtp.get_field('data_size') == 1167


if __name__ == '__main__':
    pytest.main([__file__])
