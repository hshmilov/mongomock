{
    'email': function (value) {
        return {
            'type': 'query',
            'module': 'users',
            'filter': 'specific_data.data.mail == regex("'+value+'", "i")'
        }
    }
}