import { REQUEST_API } from '../actions'

export const SAVE_QUERY = 'SAVE_QUERY'
export const UPDATE_QUERY = 'UPDATE_QUERY'
export const ADD_QUERY = 'ADD_QUERY'
export const RESTART_QUERIES = 'RESTART_QUERIES'
export const UPDATE_QUERIES = 'UPDATE_QUERIES'
export const FETCH_QUERIES = 'FETCH_QUERIES'

export const query = {
	state: {
		currentQuery: {},
		executedQueries: {fetching: false, data: [], error: ''},
		savedQueries: {fetching: false, data: [], error: ''},

		fields: [
			{path: 'query', name: 'query', default: true},
			{path: 'device_count', name: 'Devices', default: true},
			{path: 'timestamp', name: 'Date / Time', default: true}
		]

	},
	getters: {},
	mutations: {
		[ADD_QUERY] (state, payload) {
			state.savedQueries.data.push(payload)
		},
		[UPDATE_QUERY] (state, payload) {
			state.currentQuery = {}
			Object.keys(payload).forEach(function(queryKey) {
				if (payload[queryKey] && payload[queryKey].length) {
					state.currentQuery[queryKey] = payload[queryKey]
				}
			})
		},
		[ RESTART_QUERIES ] (state) {
			state.savedQueries.data = []
		},
		[ UPDATE_QUERIES ] (state, payload) {
			/* Freshly fetched devices are added to currently stored devices */
			state.savedQueries.fetching = payload.fetching
			if (payload.data) {
				let processedData = []
				payload.data.forEach(function (query) {
					let advancedQueryParts = []
					query.query = JSON.parse(query.query)
					Object.keys(query.query).forEach(function (key) {
						if (query.query[key] === undefined || !query.query[key]) { return }
						if (typeof query.query[key] === 'string') {
							advancedQueryParts.push(`${key}=${query.query[key]}`)
						} else if (typeof query.query[key] === 'object') {
							advancedQueryParts.push(`${key} in (${query.query[key]})`)
						}
					})
					query.query = advancedQueryParts.join(' AND ')
					processedData.push(query)
				})
				state.savedQueries.data = [...state.savedQueries.data, ...processedData]
			}
			if (payload.error) {
				state.savedQueries.error = payload.error
			}
		}
	},
	actions: {
		[ FETCH_QUERIES ] ({dispatch, commit}, payload) {
			/* Fetch list of queries for requested page and filtering */
			if (!payload.skip) { payload.skip = 0 }
			/* Getting first page - empty table */
			if (payload.skip === 0) { commit(RESTART_QUERIES) }
			dispatch(REQUEST_API, {
				rule: `api/queries?limit=${payload.limit}&skip=${payload.skip}`,
				type: UPDATE_QUERIES
			})
		},
		[ SAVE_QUERY ] ({dispatch, commit}, payload) {
			if (!payload.query) { return }
			if (!payload.name) { payload.name = payload.query }
			dispatch(REQUEST_API, {
				rule: 'api/queries',
				method: 'POST',
				data: payload
			}).then((response) => {
				if (response !== '') {
					return
				}
				commit(ADD_QUERY, payload)
			}).catch(() => {

			})
		}
	}
}