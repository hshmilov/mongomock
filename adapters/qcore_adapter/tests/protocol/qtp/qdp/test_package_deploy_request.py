import pytest
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage


class TestPackageDeploy(object):

    def test_request(self):
        buff = bytearray(
            b'\xbb\xdd\xdc\x00g\x05\t\x03\x00\x00\x9c\x91\nQSPR017771\x06dl.binYhttps://192.168.0.191:8443/depository/druglib/e301aee8-a067-468f-8a76-b0d75edbd616/dl.bin\x00\x01\xe8\x8f\x16\xd6\xdb^\rDrugLibUpdate\xe8\x8f\x16\xd6\xdb^W\x00i\x00"f8ebed6d8b743426be821d877687c54a59\x07SHA-256\x08Sapphire\x03MCU\x07DRUGLIB:\xbfs\xe3-\xdc\xce\x81\xcc')
        m = QtpMessage()
        m.extend_bytes(buff)
        assert m.has_field('PackageDeployRequestMessage')


if __name__ == '__main__':
    pytest.main([__file__])
