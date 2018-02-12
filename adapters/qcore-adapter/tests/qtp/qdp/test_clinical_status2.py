import pytest
from protocol.qtp.qtp_message import QtpMessage
from test_helpers.qcore_fake_pump import CLINICAL_STATUS_CONNECTIVITY_UPDATE


class TestTimeSync(object):

    def test_timesync_from_pump(self):
        qtp = QtpMessage()
        qtp.extend_bytes(bytes=CLINICAL_STATUS_CONNECTIVITY_UPDATE)
        csi_elements = qtp.get_field('csi_elements')
        assert len(csi_elements) == 4
        assert qtp.get_field('qdp_message_type') == 'ClinicalStatusConnectivityUpdate'
        item_types = [item.csi_item_type for item in csi_elements]
        assert sorted(['Connectivity', 'Power', 'InfuserStatus', 'Alarm']) == sorted(item_types)


if __name__ == '__main__':
    pytest.main([__file__])
