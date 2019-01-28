{
    'last_used_users': function (value) {
        let filter_line = 'specific_data.data.username == regex("'+value+'", "i")'
        let split_slash = value.split('\\')
        let split_at = value.split('@')
        if (split_slash.length > 1) {
            filter_line = 'specific_data.data.username == regex("'+split_slash[1]+'", "i") and specific_data.data.domain == regex("' + split_slash[0] +'", "i")'
        }
        if (split_at.length > 1) {
            filter_line = 'specific_data.data.username == regex("' + split_at[0] + '", "i") and specific_data.data.domain == regex("' + split_at[1] + '", "i")'
        }
        return {
            'type': 'query',
            'module': 'users',
            'filter': filter_line
        }
    },
    'shodan_data.vulns.vuln_name': function (value) {
        return {
            'type': 'link',
            'href': 'https://www.google.com/search?q=' + value
        }
    }
}