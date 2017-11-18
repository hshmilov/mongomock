import { REQUEST_API } from '../actions'

export const SAVE_QUERY = 'SAVE_QUERY'
export const UPDATE_QUERY = 'UPDATE_QUERY'
export const ADD_SAVED_QUERY = 'ADD_SAVED_QUERY'
export const REMOVE_SAVED_QUERY = 'REMOVE_SAVED_QUERY'
export const ADD_EXECUTED_QUERY = 'ADD_EXECUTED_QUERY'
export const RESTART_QUERIES = 'RESTART_QUERIES'
export const UPDATE_SAVED_QUERIES = 'UPDATE_SAVED_QUERIES'
export const FETCH_SAVED_QUERIES = 'FETCH_SAVED_QUERIES'
export const UPDATE_EXECUTED_QUERIES = 'UPDATE_EXECUTED_QUERIES'
export const FETCH_EXECUTED_QUERIES = 'FETCH_EXECUTED_QUERIES'
export const USE_SAVED_QUERY = 'USE_SAVED_QUERY'
export const ARCHIVE_SAVED_QUERY = 'ARCHIVE_SAVED_QUERY'


export const strToQuery = (str) => {
	let query = {}
	if (!str) {
		return query
	}
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

const addExecutedQuery = (state, query) => {
	if (Object.keys(query).length) {
		state.executedQueries.data = [ query, ...state.executedQueries.data ]
	}
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
			andParts.push(`(${orParts.join(' OR ')})`)
		}
	})
	if (!andParts.length) {
		return '*'
	}
	return andParts.join(' AND ')
}

const pad2 = (number) => {
	if ((number + '').length === 2) { return number }
	return `0${number}`
}

const getTimeDate = (fromDate) => {
	let d = new Date()
	if (fromDate) {
		d = new Date(fromDate)
	}
	return {
		date: `${pad2(d.getDate())}/${pad2(d.getMonth()+1)}/${pad2(d.getFullYear())}`,
		time: `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
	}
}

const updateQueries = (currentQueries, payload) => {
	/* Freshly fetched devices are added to currently stored devices */
	currentQueries.fetching = payload.fetching
	if (payload.data) {
		let processedData = []
		payload.data.forEach(function (currentQuery) {
			let d = getTimeDate(currentQuery.timestamp)
			processedData.push({ ...currentQuery,
				query: queryToStr(JSON.parse(currentQuery.query)),
				'timestamp.date': d.date, 'timestamp.time': d.time
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
		param += `&filter=${JSON.stringify(payload.filter)}`
	}
	dispatch(REQUEST_API, {
		rule: `api/queries${param}`,
		type: payload.type
	})
}

export const query = {
	state: {
		currentQuery: {},
		executedQueries: {fetching: false, data: [], error: ''},
		savedQueries: {fetching: false, data: [], error: ''},

		savedFields: [
			{path: 'query_name', name: 'Name', default: true},
			{path: 'query', name: 'query', default: true},
			{path: 'timestamp.date', name: 'Date', default: true},
			{path: 'timestamp.time', name: 'Time', default: true}
		],
		executedFields: [
			{path: 'query', name: 'query', default: true},
			{path: 'device_count', name: 'Devices', default: true},
			{path: 'timestamp.date', name: 'Date', default: true},
			{path: 'timestamp.time', name: 'Time', default: true}
		]

	},
	getters: {},
	mutations: {
		[ADD_SAVED_QUERY] (state, payload) {
			let d = getTimeDate()
			state.savedQueries.data = [ { ...payload,
				query: queryToStr(JSON.parse(payload.query)),
				'timestamp.date': d.date, 'timestamp.time': d.time
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
			let d = getTimeDate()
			addExecutedQuery(state, {
				query: queryToStr(state.currentQuery),
				'timestamp.date': d.date,
				'timestamp.time': d.time
			})
		},
		[ RESTART_QUERIES ] (state) {
			state.savedQueries.data = []
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
			state.currentQuery = strToQuery(requestedQuery[0].query)
			let d = getTimeDate()
			addExecutedQuery(state, {
				query: requestedQuery[0].query,
				'timestamp.date': d.date,
				'timestamp.time': d.time
			})
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
			if (!payload.query) { return }
			if (!payload.name) { payload.name = payload.query }
			dispatch(REQUEST_API, {
				rule: 'api/queries',
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
		[ ARCHIVE_SAVED_QUERY ] ({dispatch, commit}, payload) {
			if (!payload) { return }
			dispatch(REQUEST_API, {
				rule: `api/queries/${payload}`,
				method: 'DELETE'
			}).then((response) => {
				if (response !== '') {
					return
				}
				commit(REMOVE_SAVED_QUERY, payload)
			})
		}
	}
}