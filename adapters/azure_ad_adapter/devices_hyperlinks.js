{
    'user_principal_name': function (value) {
        return {
            'type': 'query',
            'module': 'users',
            'filter': '(adapters_data.azure_ad_adapter.ad_user_principal_name == "'+value+'")'
        }
    }
}