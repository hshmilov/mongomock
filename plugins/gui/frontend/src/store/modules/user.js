

export const user = {
	state: {
		data: {
			content: {data: [], fetching: false, error: ''},
			count: {data: 0, fetching: false, error: ''},
			view: {
				page: 0, pageSize: 20, fields: [
					'specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
					'specific_data.data.last_seen', 'specific_data.data.is_admin',
				], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
			},
			fields:  {data: [], fetching: false, error: ''},
			queries: {
				saved: { data: [], fetching: false, error: ''},
				history: { data: [], fetching: false, error: ''}
			}
		}
	}
}