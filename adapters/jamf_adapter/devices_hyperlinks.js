{
    'jamf_location.email_address': function (value) {
        return {
            'type': 'query',
            'module': 'users',
            'filter': 'specific_data.data.mail == regex("'+value+'", "i")'
        }
    },
    'jamf_location.username': function (value) {
        return {
            'type': 'query',
            'module': 'users',
            'filter': 'specific_data.data.username  == regex("'+value+'", "i")'
        }
    }
}