import pytest

from qcore_adapter.protocol.qtp.qdp.clinical.aperiodic_infusion_state import parse_rate


class TestParseUnits(object):

    def test_grams_hr_kg(self):
        expected = parse_rate(34565)
        assert expected == 'gr/kg/hr'

    def test_nounit(self):
        expected = parse_rate(32768)
        assert expected == 'N/A'


if __name__ == '__main__':
    pytest.main([__file__])
