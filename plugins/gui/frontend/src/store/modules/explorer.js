export const UPDATE_SEARCH_VALUE = 'UPDATE_SEARCH_VALUE'

export const explorer = {
    state: {
        searchValue: '',
        devices: {
            content: { data: [], fetching: false, error: '', rule: ''},
            count: { data: 0, fetching: false, error: ''},
            view: {
                page: 0, pageSize: 20, fields: [
                    'adapters',
                    'specific_data.data.hostname',
                    'specific_data.data.name',
                    'specific_data.data.network_interfaces.ips',
                    'specific_data.data.network_interfaces.mac',
                    'specific_data.data.last_used_users',
                    'labels'
                ], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
            }
        },
        users: {
            content: { data: [], fetching: false, error: '', rule: ''},
            count: { data: 0, fetching: false, error: ''},
            view: {
                page: 0, pageSize: 20, fields: [
                    'adapters',
                    'specific_data.data.username',
                    'specific_data.data.mail',
                    'specific_data.data.first_name',
                    'specific_data.data.last_name',
                    'labels'
                ], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
            }
        }
    },
    mutations: {
        [ UPDATE_SEARCH_VALUE ] (state, searchValue) {
            state.searchValue = searchValue
        }
    }
}
