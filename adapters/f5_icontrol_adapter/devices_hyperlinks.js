{
    'pool_name': function (value) {
        return {
            'type': 'query',
            'module': 'devices',
            'filter': 'adapters_data.f5_icontrol_adapter.pool_name == regex("'+value+'", "i")'
        }
    }
}
