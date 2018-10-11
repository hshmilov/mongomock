import itertools
import uuid

from axonius.correlator_base import CorrelationResult
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from static_users_correlator.engine import StaticUserCorrelatorEngine


def correlate(devices):
    x = list(StaticUserCorrelatorEngine().correlate(devices))
    return x


def test_empty():
    assert len(correlate([])) == 0


def get_raw_tag(associated_adapter_unique_name, associated_adapter_name, associated_adapter_id,
                mail=None):
    generated_unique_name = str(uuid.uuid1())
    generate_name = str(uuid.uuid1())
    return {
        'association_type': 'Tag',
        'associated_adapters': [
            [
                associated_adapter_unique_name, associated_adapter_id
            ]
        ],
        'associated_adapter_plugin_name': associated_adapter_name,
        'name': generated_unique_name,
        'data': {
            'mail': mail,
        },
        'type': 'adapterdata',
        'entity': 'devices',
        'action_if_exists': 'update',
        PLUGIN_UNIQUE_NAME: generated_unique_name,
        'plugin_name': generate_name
    }


def get_raw_device(mail=None, tag_data=None, principle_name=None):
    generated_unique_name = str(uuid.uuid1())
    generate_name = str(uuid.uuid1())
    generated_id = str(uuid.uuid1())
    val = {
        'tags': [],
        'adapters': [
            {
                'plugin_name': generate_name,
                PLUGIN_UNIQUE_NAME: generated_unique_name,
                'data': {
                    'id': generated_id,
                    'mail': mail,
                    'ad_user_principal_name': principle_name
                }
            }
        ],
    }
    if tag_data:
        val['tags'] = [get_raw_tag(generated_unique_name, generate_name, generated_id, *data) for data in tag_data]
    return val


def test_no_correlation():
    devices = [get_raw_device(mail='asdasd@asdasd.com'),
               get_raw_device(mail='')
               ]
    results = correlate(devices)
    assert len(results) == 0


def plugin_name(adapter):
    return adapter[PLUGIN_UNIQUE_NAME]


def device_id(adapter):
    return adapter['data']['id']


def assert_correlation(result, adapter1, adapter2):
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapters) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapters
    assert ((plugin_name(adapter1) == first_name and plugin_name(adapter2) == second_name) or
            (plugin_name(adapter1) == second_name and plugin_name(adapter2) == first_name))
    assert ((device_id(adapter1) == first_id and device_id(adapter2) == second_id) or
            (device_id(adapter1) == second_id and device_id(adapter2) == first_id))


def assert_success(results, device_list, reason, intended):
    intended_correlations = 0
    for result in results:
        if result.data['Reason'] == reason:
            intended_correlations += 1
            correlation_success = False
            adapters = [adapter for device in device_list for adapter in device['adapters']]
            for device1, device2 in itertools.combinations(adapters, 2):
                try:
                    assert_correlation(result, device1, device2)
                    correlation_success = True
                except AssertionError:
                    pass
            assert correlation_success
    assert intended_correlations == intended


def test_rule_mail_correlation():
    """
    Test a very simple correlation that should happen
    because mail
    :return:
    """
    device1 = get_raw_device(mail='test@test.com')
    device2 = get_raw_device(mail='test@test.com')
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same mail', 1)


def test_rule_principle_name_instead_of_mail():
    """
    Test a very simple correlation that should happen
    because mail
    :return:
    """
    device1 = get_raw_device(mail='test@test.com')
    device2 = get_raw_device(principle_name='test@test.com')
    assert_success(correlate([device1, device2]), [device1, device2], 'They have the same mail', 1)


def test_rule_mail_no_correlation():
    """
    Test a very simple correlation that should'nt happen because of bad mail
    :return:
    """
    device1 = get_raw_device(mail='testIncorrectMailFormat')
    device2 = get_raw_device(mail='testIncorrectMailFormat')
    device3 = get_raw_device(mail='testIncorrectMailFormat@try2')  # No dot in the mail so it shouldn't work
    device4 = get_raw_device(mail='testIncorrectMailFormat@try2')
    assert len(correlate([device1, device2, device3, device4])) == 0


if __name__ == '__main__':
    import pytest

    pytest.main([__file__])
