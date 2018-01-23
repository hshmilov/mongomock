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

export const matchToVal = (match) => {
	/*
		Convert given match of type string to the appropriate type, according to its value.
		If it is surrounded with quotes - its a string
		If its value is 'true' or 'false', its a boolean with that value
		Otherwise, it should be a number
	 */
	let strMatch = match.match(/"(.*)"/)
	if (strMatch && strMatch.length === 2) {
		return strMatch[1]
	} else if (match === 'false') {
		return false
	} else if (match === 'true') {
		return true
	}
	return parseInt(match)
}

export const queryToStr = (query) => {
	/*
		Given query is expected to be an object where values are either primitives or an array of primitives,
		e.g. {
			'field1': 'value1', 'field2': value2,
			'field3': [ value3.1, value3.2 ]
		}
	 */
	let fieldParts = []
	Object.keys(query).forEach(function (andKey) {
		if (query[andKey] === undefined) { return }
		if (typeof query[andKey] === 'object') {
			/* Items of array are separated as OR between value of the key field */
			let valueParts = []
			query[andKey].forEach(function(orKey) {
				if (typeof orKey === 'string') {
					valueParts.push(`${andKey}=="${orKey}"`)
				} else {
					valueParts.push(`${andKey}==${orKey}`)
				}
			})
			if (!valueParts.length) { return }
			if (valueParts.length === 1) {
				fieldParts.push(valueParts[0])
			} else {
				fieldParts.push(`(${valueParts.join(' and ')})`)
			}
		} else if (typeof query[andKey] === 'string') {
			fieldParts.push(`${andKey}=="${query[andKey]}"`)
		} else {
			fieldParts.push(`${andKey}==${query[andKey]}`)
		}
	})
	if (!fieldParts.length) {
		return ''
	}
	return fieldParts.join(' and ')
}

const updateQueries = (currentQueries, payload) => {
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
		currentQueries.data = [...currentQueries.data, ...processedData]
	}
	if (payload.error) {
		currentQueries.error = payload.error
	}
}

const fetchQueries = (dispatch, payload) => {
	/* Fetch list of queries for requested page and filtering */
	if (!payload.skip) { payload.skip = 0 }
	let param = `?limit=${payload.limit}&skip=${payload.skip}`
	if (payload.filter) {
		param += `&filter=${payload.filter}`
	}
	dispatch(REQUEST_API, {
		rule: `/api/queries${param}`,
		type: payload.type
	})
}

export const query = {
	state: {
		currentQuery: "",
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
		]

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
			state.savedQueries.data = [ { ...payload,
				query_name: payload.name,
				filter: payload.filter,
				'timestamp': new Date().getTime()
			}, ...state.savedQueries.data ]
		},
		[REMOVE_SAVED_QUERY] (state, payload) {
			state.savedQueries.data = [ ...state.savedQueries.data ].filter(function(query) {
				return query.id !== payload
			})
		},
		[UPDATE_QUERY] (state, payload) {
			state.currentQuery = payload
			state.executedQueries.data = []
		},
		[ UPDATE_SAVED_QUERIES ] (state, payload) {
			updateQueries(state.savedQueries, payload)
		},
		[ UPDATE_EXECUTED_QUERIES ] (state, payload) {
			updateQueries(state.executedQueries, payload)
		},
		[ USE_SAVED_QUERY ] (state, payload) {
			let requestedQuery = state.savedQueries.data.filter(function(savedQuery) {
				return savedQuery.id === payload
			})
			state.currentQuery = requestedQuery[0].filter
			state.executedQueries.data = []
		}
	},
	actions: {
		[ FETCH_SAVED_QUERIES ] ({dispatch}, payload) {
			payload.type = UPDATE_SAVED_QUERIES
			if (!payload.filter) {
				payload.filter = "query_type == 'saved'"
			} else {
				payload.filter = `(${payload.filter}) and query_type == 'saved'`
			}
			fetchQueries(dispatch, payload)
		},
		[ FETCH_EXECUTED_QUERIES ] ({dispatch}, payload) {
			payload.type = UPDATE_EXECUTED_QUERIES
			if (!payload.filter) {
				payload.filter = "query_type == 'history'"
			} else {
				payload.filter = `(${payload.filter}) and query_type == 'history'`
			}
			fetchQueries(dispatch, payload)
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
				if (response !== '') {
					return
				}
				commit(REMOVE_SAVED_QUERY, queryId)
			})
		}
	}
}