{
    'aws_load_balancers.name': function (value) {
        return {
            'type': 'query',
            'module': 'devices',
            'filter': 'adapters_data.aws_adapter.aws_load_balancers.name == regex("'+value+'", "i")'
        }
    }
}