import axios from 'axios'
import Promise from 'promise'

import { INIT_USER } from './modules/auth'
import {
	UPDATE_DATA_CONTENT, UPDATE_DATA_COUNT,
	UPDATE_DATA_VIEWS, ADD_DATA_VIEW,
	UPDATE_DATA_FIELDS, UPDATE_DATA_QUERIES, ADD_DATA_QUERY, UPDATE_REMOVED_DATA_QUERY,
	UPDATE_DATA_LABELS, UPDATE_ADDED_DATA_LABELS, UPDATE_REMOVED_DATA_LABELS, UPDATE_DATA_BY_ID
} from './mutations'

let host = ''
// if (process.env.NODE_ENV !== 'production') {
// 	host = 'http://10.0.240.119'
// }

/*
    A generic wrapper for requests to server.
    Before request, performs given mutation to initialize error and indicate fetching in process,
    After request, performs given mutation with controls received or error thrown, accordingly

    @param {commit} - Vue action mechanism provides this
    @param payload - An object containing: {
        method: HTTP method for the request [defaulted GET]
        rule: Entry in the API to call, including request parameters, if needed
        controls: Object with controls, for HTTP methods that allow sending it, if needed,
        type: Mutation type to call
    }
 */
export const REQUEST_API = 'REQUEST_API'
export const requestApi = ({commit}, payload) => {
	if (!payload.rule) return

	if (payload.type) {
		commit(payload.type, {fetching: true, error: '', ...payload.payload})
	}
	if (!payload.method) payload.method = 'GET'

	let request_config = {method: payload.method, url: `${host}/api/${payload.rule}`/*, withCredentials: true*/}
	if (payload.data) request_config['data'] = payload.data
	return new Promise((resolve, reject) => axios(request_config)
		.then((response) => {
			if (payload.type) {
				commit(payload.type, {fetching: false, data: response.data, ...payload.payload})
			}
			resolve(response)
		})
		.catch((error) => {
			let errorMessage = error.message
			if (error && error.response) {
				if (error.response.status === 401) {
					commit(INIT_USER, {fetching: false, error: errorMessage})
					return
				}
				if (error.response.status >= 500) {
					errorMessage = 'Verify all services are up and registered'
				} else if (error.response.data && error.response.data.message) {
					errorMessage = error.response.data.message
				}
			}
			if (payload.type) {
				commit(payload.type, {fetching: false, error: errorMessage})
			}
			reject(error)
		}))
}

export const validModule = (state, payload) => {
	return (payload && payload.module && state[payload.module])
}

export const FETCH_DATA_COUNT = 'FETCH_DATA_COUNT'
export const fetchDataCount = ({state, dispatch}, payload) => {
	if (!validModule(state, payload)) return
	const view = state[payload.module].view

	let param = (view.query && view.query.filter) ? `?filter=${view.query.filter}` : ''
	dispatch(REQUEST_API, {
		rule: `${payload.module}/count${param}`,
		type: UPDATE_DATA_COUNT,
		payload
	})
}

const createContentRequest = (state, payload) => {
	if (!validModule(state, payload)) return ''
	const view = state[payload.module].view

	let params = []
	if (payload.skip !== undefined) {
		params.push(`skip=${payload.skip}`)
	}
	if (payload.limit !== undefined) {
		params.push(`limit=${payload.limit}`)
	}
	if (view.fields && view.fields.length) {
		params.push(`fields=${view.fields}`)
	}
	if (view.query && view.query.filter) {
		params.push(`filter=${encodeURI(view.query.filter)}`)
	}
	if (view.sort && view.sort.field) {
		params.push(`sort=${view.sort.field}${view.sort.desc? '-' : '+'}`)
	}
	return params.join('&')
}

export const FETCH_DATA_CONTENT = 'FETCH_DATA_CONTENT'
export const fetchDataContent = ({state, dispatch}, payload) => {
	if (!payload.skip) {
		dispatch(FETCH_DATA_COUNT, {module: payload.module})
	}
	return dispatch(REQUEST_API, {
		rule: `${payload.module}?${createContentRequest(state, payload)}`,
		type: UPDATE_DATA_CONTENT,
		payload: {module: payload.module, skip: payload.skip}
	})
}

export const FETCH_DATA_CONTENT_CSV = 'FETCH_DATA_CONTENT_CSV'
export const fetchDataContentCSV = ({state, dispatch}, payload) => {

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/csv?${createContentRequest(state, payload)}`,
		payload: {module: payload.module, skip: payload.skip}
	}).then((response) => {
		let blob = new Blob([response.data], { type: response.headers["content-type"]} )
		let link = document.createElement('a')
		link.href = window.URL.createObjectURL(blob)
		link.download = 'export.csv'
		link.click()
	})
}

export const FETCH_DATA_VIEWS = 'FETCH_DATA_VIEWS'
export const fetchDataViews = ({state, dispatch}, payload) => {
	if (!validModule(state, payload)) return
	dispatch(REQUEST_API, {
		rule: payload.module + '/views',
		type: UPDATE_DATA_VIEWS,
		payload: {module: payload.module}
	})
}

export const SAVE_DATA_VIEW = 'SAVE_DATA_VIEW'
export const saveDataView = ({state, dispatch, commit}, payload) => {
	if (!validModule(state, payload)) return
	let viewObj = {name: payload.name, view: state[payload.module].view}
	dispatch(REQUEST_API, {
		rule: payload.module + '/views',
		data: viewObj,
		method: 'POST'
	}).then((response) => {
		if (response.status === 200) {
			commit(ADD_DATA_VIEW, {module: payload.module, ...viewObj})
		}
	}).catch(console.log.bind(console))
}

export const FETCH_DATA_FIELDS = 'FETCH_DATA_FIELDS'
export const fetchDataFields = ({state, dispatch}, payload) => {
	if (!validModule(state, payload)) return
	dispatch(REQUEST_API, {
		rule: payload.module + '/fields',
		type: UPDATE_DATA_FIELDS,
		payload: {module: payload.module}
	})
}

export const FETCH_DATA_QUERIES = 'FETCH_DATA_QUERIES'
export const fetchDataQueries = ({state, dispatch}, payload) => {
	if (!validModule(state, payload) || !payload.type) return
	if (!payload.skip) payload.skip = 0
	if (!payload.limit) payload.limit = 1000

	let filter = `query_type=='${payload.type}'`
	if (payload.filter) {
		filter += ` and ${payload.filter}`
	}
	let param = `?limit=${payload.limit}&skip=${payload.skip}&filter=${encodeURI(filter)}`
	dispatch(REQUEST_API, {
		rule: `${payload.module}/queries${param}`,
		type: UPDATE_DATA_QUERIES,
		payload: {module: payload.module, type: payload.type, skip: payload.skip}
	})
}

export const SAVE_DATA_QUERY = 'SAVE_DATA_QUERY'
export const saveDataQuery = ({state, dispatch, commit}, payload) => {
	if (!validModule(state, payload) || !payload.name) return
	let queryObj = {name: payload.name, ...state[payload.module].view.query }
	return dispatch(REQUEST_API, {
		rule: payload.module + '/queries',
		method: 'POST',
		data: queryObj
	}).then((response) => {
		if (response.status === 200 && response.data) {
			commit(ADD_DATA_QUERY, {
				module: payload.module, query: { ...queryObj, uuid: response.data}
			})
		}
	}).catch(console.log.bind(console))
}

export const REMOVE_DATA_QUERY = 'REMOVE_DATA_QUERY'
export const removeDataQuery = ({state, dispatch, commit}, payload) => {
	if (!validModule(state, payload) || !payload.id) return

	dispatch(REQUEST_API, {
		rule: `${payload.module}/queries/${payload.id}`,
		method: 'DELETE'
	}).then((response) => {
		if (response.data !== '') {
			return
		}
		commit(UPDATE_REMOVED_DATA_QUERY, payload)
	})
}

export const START_RESEARCH_PHASE = 'START_RESEARCH_PHASE'
export const startResearch= ({dispatch}) => {
    dispatch(REQUEST_API, {
        rule: `research_phase`,
        method: 'POST'
    })
}

export const FETCH_DATA_LABELS = 'FETCH_DATA_LABELS'
export const fetchDataLabels = ({state, dispatch}, payload) => {
	if (!validModule(state, payload)) return
	dispatch(REQUEST_API, {
		rule: `${payload.module}/labels`,
		type: UPDATE_DATA_LABELS,
		payload: {module: payload.module}
	})
}

export const ADD_DATA_LABELS = 'ADD_DATA_LABELS'
export const addDataLabels = ({state, dispatch, commit}, payload) => {
	if (!validModule(state, payload)) return

	if (!payload.data || !payload.data.entities || !payload.data.entities.length
		|| !payload.data.labels || !payload.data.labels.length) {
		return
	}

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/labels`,
		method: 'POST',
		data: payload.data
	}).then(() => commit(UPDATE_ADDED_DATA_LABELS, payload))
}

export const REMOVE_DATA_LABELS = 'REMOVE_DATA_LABELS'
export const removeDataLabels = ({state, dispatch, commit}, payload) => {
	if (!validModule(state, payload)) return

	if (!payload.data || !payload.data.entities || !payload.data.entities.length
		|| !payload.data.labels || !payload.data.labels.length) {
		return
	}

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/labels`,
		method: 'DELETE',
		data: payload.data
	}).then(() => commit(UPDATE_REMOVED_DATA_LABELS, payload))
}

export const DISABLE_DATA = 'DISABLE_DATA'
export const disableData = ({state, dispatch}, payload) => {
	if (!validModule(state, payload)) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/disable`,
		method: 'POST',
		data: payload.data
	})
}

export const FETCH_DATA_BY_ID = 'FETCH_DATA_BY_ID'
export const fetchDataByID = ({state, dispatch}, payload) => {
	if (!validModule(state, payload)) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/${payload.id}`,
		type: UPDATE_DATA_BY_ID,
		payload
	})
}