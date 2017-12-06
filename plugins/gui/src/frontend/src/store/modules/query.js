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


export const strToQuery = (str) => {
	let query = {}
	if (!str || str === '*') { return query }
	let andParts = str.split(' AND ')
	andParts.forEach(function (andPart) {
		let matchObject = andPart.match(/\(.*\)/)
		let orParts = andPart.split(' OR ')
		if (orParts.length < 1) { return }
		let matchValues = orParts[0].match(/\(?(.*)(=)([^\)]*)\)?/)
		if (matchValues === undefined || matchValues.length < 4) { return }
		if (matchObject === undefined || matchObject === null) {
			query[matchValues[1]] = matchValues[3]
		} else {
			query[matchValues[1]] = [ matchValues[3] ]
			orParts.splice(1).forEach(function(orPart) {
				matchValues = orPart.match(/\(?(.*)(=)([^\)]*)\)?/)
				if (matchValues === undefined || matchValues.length < 4) { return }
				query[matchValues[1]].push(matchValues[3])
			})
		}
	})
	return query
}

export const queryToStr = (query) => {
	let andParts = []
	Object.keys(query).forEach(function (andKey) {
		if (query[andKey] === undefined || !query[andKey]) { return }
		if (typeof query[andKey] === 'string') {
			andParts.push(`${andKey}=${query[andKey]}`)
		} else if (typeof query[andKey] === 'object') {
			let orParts = []
			query[andKey].forEach(function(orKey) {
				orParts.push(`${andKey}=${orKey}`)
			})
			if (!orParts.length) { return }
			andParts.push(`(${orParts.join(' OR ')})`)
		}
	})
	if (!andParts.length) {
		return '*'
	}
	return andParts.join(' AND ')
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
				filter: queryToStr(JSON.parse(currentQuery.filter))
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
	if (!payload.limit) { payload.limit = -1 }
	let param = `?limit=${payload.limit}&skip=${payload.skip}`
	if (payload.filter) {
		param += `&filter=${JSON.stringify(payload.filter)}`
	}
	dispatch(REQUEST_API, {
		rule: `/api/queries${param}`,
		type: payload.type
	})
}

export const query = {
	state: {
		currentQuery: {},
		executedQueries: {fetching: false, data: [], error: ''},
		savedQueries: {fetching: false, data: [], error: ''},

		savedFields: [
			{path: 'name', name: 'Name', default: true},
			{path: 'filter', name: 'Query', default: true},
			{path: 'timestamp', name: 'Save Time', type: 'timestamp', default: true},
		],
		executedFields: [
			{path: 'filter', name: 'Query', default: true},
			{path: 'device_count', name: 'Devices', default: true},
			{path: 'timestamp', name: 'Execution Time', type: 'timestamp', default: true},
		]

	},
	getters: {
		savedQueryOptions(state) {
			return state.savedQueries.data.map(function(query_obj) {
				return {
					value: query_obj.raw_filter,
					name: query_obj.query_name
				}
			})
		}
	},
	mutations: {
		[ADD_SAVED_QUERY] (state, payload) {
			if (!state.savedQueries.data || !state.savedQueries.data.length) { return }
			state.savedQueries.data = [ { ...payload,
				query_name: payload.name,
				filter: queryToStr(payload.filter),
				'timestamp': new Date().getTime()
			}, ...state.savedQueries.data ]
		},
		[REMOVE_SAVED_QUERY] (state, payload) {
			state.savedQueries.data = [ ...state.savedQueries.data ].filter(function(query) {
				return query.id !== payload
			})
		},
		[UPDATE_QUERY] (state, payload) {
			state.currentQuery = {}
			Object.keys(payload).forEach(function(queryKey) {
				if (payload[queryKey] && payload[queryKey].length) {
					state.currentQuery[queryKey] = payload[queryKey]
				}
			})
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
			state.currentQuery = JSON.parse(requestedQuery[0].raw_filter)
			state.executedQueries.data = []
		}
	},
	actions: {
		[ FETCH_SAVED_QUERIES ] ({dispatch}, payload) {
			payload.type = UPDATE_SAVED_QUERIES
			if (!payload.filter) { payload.filter = {} }
			payload.filter.query_type = 'saved'
			fetchQueries(dispatch, payload)
		},
		[ FETCH_EXECUTED_QUERIES ] ({dispatch}, payload) {
			payload.type = UPDATE_EXECUTED_QUERIES
			if (!payload.filter) { payload.filter = {} }
			payload.filter.query_type = 'history'
			fetchQueries(dispatch, payload)
		},
		[ SAVE_QUERY ] ({dispatch, commit}, payload) {
			if (!payload.filter) { return }
			if (!payload.name) { payload.name = payload.filter }
			dispatch(REQUEST_API, {
				rule: '/api/queries',
				method: 'POST',
				data: payload
			}).then((response) => {
				if (response === '') {
					return
				}
				if (payload.callback !== undefined) {
					payload.callback()
				}
				payload.id = response
				commit(ADD_SAVED_QUERY, payload)
			}).catch(() => {

			})
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