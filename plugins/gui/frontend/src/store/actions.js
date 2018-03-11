import axios from 'axios'
import Promise from 'promise'

import { INIT_USER } from './modules/auth'
import { UPDATE_TABLE_CONTENT, UPDATE_TABLE_COUNT, UPDATE_TABLE_VIEWS, ADD_TABLE_VIEW } from './mutations'

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
        commit(payload.type, { fetching: true, error: '', ...payload.payload })
    }
    if (!payload.method) payload.method = 'GET'

    let request_config = { method: payload.method, url: `${host}/api/${payload.rule}`/*, withCredentials: true*/ }
    if (payload.data) request_config['data'] = payload.data
    return new Promise((resolve, reject) => axios(request_config)
        .then((response) => {
            if (payload.type) {
                commit(payload.type, { fetching: false, data: response.data, ...payload.payload })
            }
            resolve(response)
        })
        .catch((error) => {
			let errorMessage = error.message
            if (error && error.response) {
                if (error.response.status === 401) {
                    commit(INIT_USER, { fetching: false, error: errorMessage })
                    return
                }
                if (error.response.status >= 500) {
                    errorMessage = "Verify all services are up and registered"
                } else if (error.response.data && error.response.data.message) {
                    errorMessage = error.response.data.message
                }
            }
            if (payload.type) {
                commit(payload.type, { fetching: false, error: errorMessage })
            }
            reject(error)
        }))
}

export const FETCH_TABLE_COUNT = 'FETCH_TABLE_COUNT'
export const fetchTableCount = ({state, dispatch}, payload) => {
	if (!payload.module || !state[payload.module] || !state[payload.module].dataTable) return
	const view = state[payload.module].dataTable.view

	let param = (view && view.filter) ? `?filter=${view.filter}` : ''
	dispatch(REQUEST_API, {
		rule: `${payload.module}/count${param}`,
		type: UPDATE_TABLE_COUNT,
		payload
	})
}


export const FETCH_TABLE_CONTENT = 'FETCH_TABLE_CONTENT'
export const fetchTableContent = ({state, dispatch}, payload) => {
    if (!payload.module || !state[payload.module] || !state[payload.module].dataTable) return
    const view = state[payload.module].dataTable.view

	if (!payload.skip) {
		payload.skip = 0
		dispatch(FETCH_TABLE_COUNT, { module: payload.module })
	}
	if (!payload.limit) payload.limit = 0

	let param = `?limit=${payload.limit}&skip=${payload.skip}`
	if (view.fields && view.fields.length) {
		param += `&fields=${view.fields}`
	}
	if (view.filter && view.filter.length) {
		param += `&filter=${view.filter}`
	}
	dispatch(REQUEST_API, {
		rule: payload.module + param,
		type: UPDATE_TABLE_CONTENT,
		payload: { module: payload.module, restart: (payload.skip === 0) }
	})
}


export const FETCH_TABLE_VIEWS = 'FETCH_TABLE_VIEWS'
export const fetchTableViews = ({state, dispatch}, payload) => {
	if (!payload.module || !state[payload.module] || !state[payload.module].dataViews) return
	dispatch(REQUEST_API, {
		rule: payload.module + '/views',
		type: UPDATE_TABLE_VIEWS,
		payload: { module: payload.module }
	})
}


export const SAVE_TABLE_VIEW = 'SAVE_TABLE_VIEW'
export const saveTableView = ({state, dispatch, commit}, payload) => {
	if (!payload.module || !state[payload.module] || !state[payload.module].dataTable) return
	let viewObj = {name: payload.name, view: state[payload.module].dataTable.view}
	dispatch(REQUEST_API, {
		rule: payload.module + '/views',
		data: viewObj,
		method: 'POST'
	}).then((response) => {
		if (response.status === 200) {
			commit(ADD_TABLE_VIEW, { module: payload.module, ...viewObj })
		}
	})
}
