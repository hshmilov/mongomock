import mongomock

from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.modules.plugin_settings import Consts, PluginSettingsNamespace, ConfigurableConfigsGeneral

CONFIG1 = {
    'option1': True,
    'option2': {
        'enabled': False,
        'string': 'x1'
    }
}


def get_mongo_client() -> mongomock.MongoClient:
    db = mongomock.MongoClient()
    db['core'][Consts.AllConfigurableConfigs].insert_many(
        [
            {
                PLUGIN_NAME: 'aws_adapter',
                Consts.ConfigName: 'config1',
                Consts.Config: CONFIG1
            },
            {
                PLUGIN_NAME: 'aws_adapter',
                Consts.ConfigName: 'config2',
                Consts.Config: {
                    'option1': True,
                    'option2': {
                        'enabled': True,
                        'string': 'x1'
                    }
                }
            },
            {
                PLUGIN_NAME: 'esx_adapter',
                Consts.ConfigName: 'config2',
                Consts.Config: {
                    'option1': True,
                    'option2': {
                        'enabled': True,
                        'string': 'x2'
                    }
                }
            },
            {
                PLUGIN_NAME: 'jamf_adapter',
                Consts.ConfigName: 'config2',
                Consts.Config: {
                    'option1': False,
                    'option2': {
                        'enabled': False,
                        'string': 'x2'
                    }
                }
            }
        ]
    )

    return db


def test_insert_config():
    db = get_mongo_client()
    namespace = PluginSettingsNamespace(db)
    config = {'c1': 'c2', 'c3': {'enabled': True}}
    namespace.get_plugin('cisco_adapter').configurable_configs.adapter_configuration = config
    # adapter_configuration == 'AdapterBase'
    assert namespace.get_plugin('cisco_adapter').configurable_configs['AdapterBase'] == config


def test_get_all_plugins_with_config():
    db = get_mongo_client()
    general = ConfigurableConfigsGeneral(db)
    assert general.get_plugin_names_with_config(
        'config1',
        {}
    ) == ['aws_adapter']

    assert general.get_plugin_names_with_config(
        'config2',
        {
            'option1': True
        }
    ) == ['aws_adapter', 'esx_adapter']

    assert general.get_plugin_names_with_config(
        'config2',
        {
            'option2.string': 'x2'
        }
    ) == ['esx_adapter', 'jamf_adapter']

    assert general.get_plugin_names_with_config(
        'config2',
        {
            'option2.string': 'x2',
            'option2.enabled': False
        }
    ) == ['jamf_adapter']

    assert general.get_plugin_names_with_config(
        'config2',
        {
            'does_not_exist': True
        }
    ) == []

    assert general.get_plugin_names_with_config(
        'config2',
        {
            'option2.string': 'x2',
            'does_not_exist': True
        }
    ) == []

    assert general.get_plugin_names_with_config(
        'config3',
        {}
    ) == []
