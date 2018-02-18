import { REQUEST_API } from '../actions'

export const SAVE_QUERY = 'SAVE_QUERY'
export const UPDATE_QUERY = 'UPDATE_QUERY'
export const ADD_SAVED_QUERY = 'ADD_SAVED_QUERY'
export const ARCHIVE_SAVED_QUERY = 'ARCHIVE_SAVED_QUERY'
export const REMOVE_SAVED_QUERY = 'REMOVE_SAVED_QUERY'
export const ADD_EXECUTED_QUERY = 'ADD_EXECUTED_QUERY'
export const UPDATE_SAVED_QUERIES = 'UPDATE_SAVED_QUERIES'
export const FETCH_SAVED_QUERIES = 'FETCH_SAVED_QUERIES'
export const UPDATE_EXECUTED_QUERIES = 'UPDATE_EXECUTED_QUERIES'
export const FETCH_EXECUTED_QUERIES = 'FETCH_EXECUTED_QUERIES'
export const USE_SAVED_QUERY = 'USE_SAVED_QUERY'
export const UPDATE_NEW_QUERY = 'UPDATE_NEW_QUERY'
export const UPDATE_QUICK_SAVED = 'UPDATE_QUICK_SAVED'
export const UPDATE_QUICK_EXECUTED = 'UPDATE_QUICK_EXECUTED'


const updateQueries = (currentQueries, payload, restart) => {
	/* Freshly fetched devices are added to currently stored devices */
	currentQueries.fetching = payload.fetching
	if (payload.data) {
		let processedData = []
		payload.data.forEach(function (currentQuery) {
			processedData.push({ ...currentQuery,
				id: currentQuery.uuid,
				raw_filter: currentQuery.filter,
				filter: currentQuery.filter
			})
		})
		currentQueries.data = restart? processedData : [...currentQueries.data, ...processedData]
	}
	if (payload.error) {
		currentQueries.error = payload.error
	}
}

const fetchQueries = (dispatch, payload, queryType) => {
	/* Fetch list of queries for requested page and filtering */
	if (!payload.skip) { payload.skip = 0 }
	if (!payload.limit) {payload.limit = 2000 }
	let param = `?limit=${payload.limit}&skip=${payload.skip}`
	let filter = `query_type == '${queryType}'`
	if (payload.filter) {
		filter = `${filter} and (${payload.filter})`
	}
	param += '&filter=' + encodeURI(filter)
	dispatch(REQUEST_API, {
		rule: `/api/queries${param}`,
		type: payload.type
	})
}

export const query = {
	state: {
		executedQueries: {fetching: false, data: [], error: ''},
		savedQueries: {fetching: false, data: [], error: ''},

		savedFields: [
			{path: 'name', name: 'Name', default: true},
			{path: 'filter', name: 'Filter', default: true},
			{path: 'timestamp', name: 'Save Time', type: 'timestamp', default: true},
		],
		executedFields: [
			{path: 'filter', name: 'Filter', default: true},
			{path: 'device_count', name: 'Devices', default: true},
			{path: 'timestamp', name: 'Execution Time', type: 'timestamp', default: true},
		],

		quickQuery: {
			limit: 5,
			executedQueries: {fetching: false, data: [], error: ''},
			savedQueries: {fetching: false, data: [], error: ''}
		},
		queryDetails: { fetching: false, data: {}, error: ''},
		newQuery: {
			filter: '',
			filterExpressions: []
		}

	},
	getters: {
		savedQueryOptions(state) {
			return state.savedQueries.data.map(function(query_obj) {
				return {
					value: query_obj.id,
					name: query_obj.name,
					inUse: (query_obj['alertIds'] !== undefined && query_obj['alertIds'].length)
				}
			})
		}
	},
	mutations: {
		[ADD_SAVED_QUERY] (state, payload) {
			if (!state.savedQueries.data || !state.savedQueries.data.length) { return }
			const savedQuery = { ...payload,
				query_name: payload.name,
				filter: payload.filter,
				'timestamp': new Date().getTime()
			}
			state.savedQueries.data = [ savedQuery, ...state.savedQueries.data ]
			state.quickQuery.savedQueries.data = [ savedQuery, ...state.savedQueries.slice(0, 4)]
		},
		[REMOVE_SAVED_QUERY] (state, payload) {
			state.savedQueries.data = [ ...state.savedQueries.data ].filter(function(query) {
				return query.id !== payload
			})
		},
		[UPDATE_QUERY] (state, payload) {
			state.newQuery.filter = payload
			state.executedQueries.data = []
		},
		[ UPDATE_SAVED_QUERIES ] (state, payload) {
			updateQueries(state.savedQueries, payload)
		},
		[ UPDATE_EXECUTED_QUERIES ] (state, payload) {
			updateQueries(state.executedQueries, payload)
		},
		[ UPDATE_QUICK_SAVED ] (state, payload) {
			updateQueries(state.quickQuery.savedQueries, payload, true)
		},
		[ UPDATE_QUICK_EXECUTED ] (state, payload) {
			updateQueries(state.quickQuery.executedQueries, payload, true)
		},
		[ USE_SAVED_QUERY ] (state, payload) {
			let requestedQuery = state.savedQueries.data.filter(function(savedQuery) {
				return savedQuery.id === payload
			})
			state.newQuery.filter = requestedQuery[0].filter
			state.newQuery.filterExpressions = []
			state.executedQueries.data = []
		},
		[ UPDATE_NEW_QUERY ] (state, payload) {
			state.newQuery = { ...state.newQuery, ...payload }
		}
	},
	actions: {
		[ FETCH_SAVED_QUERIES ] ({dispatch}, payload) {
			if (!payload) { payload = {} }
			if (!payload.type) {
				payload.type = UPDATE_SAVED_QUERIES
			}
			fetchQueries(dispatch, payload, 'saved')
		},
		[ FETCH_EXECUTED_QUERIES ] ({dispatch}, payload) {
			if (!payload) { payload = {} }
			if (!payload.type) {
				payload.type = UPDATE_EXECUTED_QUERIES
			}
			fetchQueries(dispatch, payload, 'history')
		},
		[ SAVE_QUERY ] ({dispatch, commit}, payload) {
			if (!payload.filter) { return }
			if (!payload.name) { payload.name = payload.filter }
			return dispatch(REQUEST_API, {
				rule: '/api/queries',
				method: 'POST',
				data: payload
			}).then((response) => {
				if (response === '') {
					return
				}
				payload.id = response
				commit(ADD_SAVED_QUERY, payload)
			}).catch(console.log.bind(console))
		},
		[ ARCHIVE_SAVED_QUERY ] ({dispatch, commit}, queryId) {
			if (!queryId) { return }
			dispatch(REQUEST_API, {
				rule: `/api/queries/${queryId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response.data !== '') {
					return
				}
				commit(REMOVE_SAVED_QUERY, queryId)
			})
		}
	}
}