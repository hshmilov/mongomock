
export const users = {
    state: {
        content: {data: [], fetching: false, error: ''},
        count: {data: 0, fetching: false, error: ''},
        view: {
            page: 0, pageSize: 20, fields: [
                'adapters', 'specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
                'specific_data.data.last_seen', 'specific_data.data.is_admin',
            ], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
        },
        fields: {data: [], fetching: false, error: ''},
        views: {
            saved: {data: [], fetching: false, error: ''},
            history: {data: [], fetching: false, error: ''}
        },
        labels: {data: [], fetching: false, error: ''},
		current: {fetching: false, data: {}, error: ''}
    }
}