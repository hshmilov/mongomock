
export const usersFields = [
    'adapters', 'specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
    'specific_data.data.last_seen', 'specific_data.data.is_admin', 'labels'
]

export const users = {
    state: {
        content: {data: [], fetching: false, error: ''},

        count: {data: 0, fetching: false, error: ''},

        view: {
            page: 0, pageSize: 20, fields: usersFields, coloumnSizes: [], query: {
                filter: '', expressions: [], search: ''
            }, sort: {
                field: '', desc: true
            },
            historical: null
        },

        details: { data: {}, fetching: false, error: '' },

        fields: {data: [], fetching: false, error: ''},

        hyperlinks: {data: [], fetching: false, error: ''},

        views: {
            content: { data: [], fetching: false, error: '', rule: ''},
            count: { data: 0, fetching: false, error: ''},
            view: {
                page: 0, pageSize: 20, query: {
                    filter: '', expressions: [], search: ''
                }, sort: {
                    field: '', desc: true
                }
            },

            saved: {data: [], fetching: false, error: ''},

            history: {data: [], fetching: false, error: ''}
        },

        labels: {data: [], fetching: false, error: ''},

        current: {fetching: false, data: {}, error: ''}
    }
}