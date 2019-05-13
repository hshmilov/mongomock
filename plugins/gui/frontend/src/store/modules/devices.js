
export const devicesFields = [
	'adapters', 'specific_data.data.hostname', 'specific_data.data.name',
	'specific_data.data.last_seen', 'specific_data.data.os.type',
	'specific_data.data.network_interfaces.ips', 'specific_data.data.network_interfaces.mac',
	'labels'
]

export const devices = {
	state: {
		content: { data: [], fetching: false, error: '', rule: ''},

		count: { data: 0, fetching: false, error: ''},

		view: {
			page: 0, pageSize: 20, fields: devicesFields, coloumnSizes: [], query: {
				filter: '', expressions: [], search: ''
			}, sort: {
				field: '', desc: true
			},
			historical: null
		},

		details: { data: {}, fetching: false, error: '' },

		fields: { data: {}, fetching: false, error: '' },

		hyperlinks: {data: [], fetching: false, error: '' },

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

			saved: { data: [], fetching: false, error: '' },

			history: { data: [], fetching: false, error: ''}
		},

		labels: { data: [], fetching: false, error: ''},

		current: {fetching: false, data: {}, error: ''},

	}
}