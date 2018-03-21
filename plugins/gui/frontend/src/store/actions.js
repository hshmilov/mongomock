import axios from 'axios'
import Promise from 'promise'

import { INIT_USER } from './modules/auth'
import {
	UPDATE_DATA_CONTENT, UPDATE_DATA_COUNT,
	UPDATE_DATA_VIEWS, ADD_DATA_VIEW,
	UPDATE_DATA_FIELDS, UPDATE_DATA_QUERIES
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
	return (payload && payload.module && state[payload.module] && state[payload.module].data)
}

export const FETCH_DATA_COUNT = 'FETCH_DATA_COUNT'
export const fetchDataCount = ({state, dispatch}, payload) => {
	if (!validModule(state, payload)) return
	const view = state[payload.module].data.view

	let param = (view.query && view.query.filter) ? `?filter=${view.query.filter}` : ''
	dispatch(REQUEST_API, {
		rule: `${payload.module}/count${param}`,
		type: UPDATE_DATA_COUNT,
		payload
	})
}

export const FETCH_DATA_CONTENT = 'FETCH_DATA_CONTENT'
export const fetchDataContent = ({state, dispatch}, payload) => {
	if (!validModule(state, payload)) return
	const view = state[payload.module].data.view

	if (!payload.skip) {
		payload.skip = 0
		dispatch(FETCH_DATA_COUNT, {module: payload.module})
	}
	if (!payload.limit) payload.limit = 1000

	let param = `?limit=${payload.limit}&skip=${payload.skip}`
	if (view.fields && view.fields.length) {
		param += `&fields=${view.fields}`
	}
	if (view.query && view.query.filter) {
		param += `&filter=${encodeURI(view.query.filter)}`
	}
	if (view.sort && view.sort.field) {
		param += `&sort=${view.sort.field}${view.sort.desc? '-' : '+'}`
	}
	return dispatch(REQUEST_API, {
		rule: payload.module + param,
		type: UPDATE_DATA_CONTENT,
		payload: {module: payload.module, skip: payload.skip}
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
	let viewObj = {name: payload.name, view: state[payload.module].data.view}
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
	let queryObj = {name: payload.name, ...state[payload.module].data.view.query }
	return dispatch(REQUEST_API, {
		rule: payload.module + '/queries',
		method: 'POST',
		data: queryObj
	}).then((response) => {
		if (response.status === 200) {
			commit(ADD_DATA_VIEW, {module: payload.module, query: queryObj})
		}
	}).catch(console.log.bind(console))
}

export const START_RESEARCH_PHASE = 'START_RESEARCH_PHASE'
export const startResearch= ({dispatch}) => {
    dispatch(REQUEST_API, {
        rule: `research_phase`,
        method: 'POST'
    })
}