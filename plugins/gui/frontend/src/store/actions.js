import axios from 'axios'
import Promise from 'promise'

import { INIT_USER } from './modules/auth'
import {
	UPDATE_DATA_CONTENT, UPDATE_DATA_COUNT,
	UPDATE_DATA_VIEWS, ADD_DATA_VIEW, UPDATE_DATA_FIELDS,
	UPDATE_DATA_LABELS, UPDATE_ADDED_DATA_LABELS, UPDATE_REMOVED_DATA_LABELS, UPDATE_DATA_BY_ID,
    UPDATE_SAVED_DATA_NOTE, UPDATE_REMOVED_DATA_NOTE,
	UPDATE_REMOVED_DATA_VIEW, UPDATE_SYSTEM_CONFIG,
	UPDATE_DATA_HYPERLINKS
} from './mutations'

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
		commit(payload.type, {rule: payload.rule, fetching: true, error: '', ...payload.payload})
	}
	if (!payload.method) payload.method = 'GET'

	let request_config = {method: payload.method, url: `/api/${payload.rule}`}
	if (payload.data) request_config['data'] = payload.data
	if (payload.binary) request_config['responseType'] = 'arraybuffer'
	return new Promise((resolve, reject) => axios(request_config)
		.then((response) => {
			if (payload.type) {
				commit(payload.type, {
					rule: payload.rule, fetching: false, data: response.data, ...payload.payload
				})
			}
			resolve(response)
		})
		.catch((error) => {
			let errorMessage = error.message
			if (error && error.response) {
				errorMessage = error.response.data.message
				if (error.response.status === 401) {
					commit(INIT_USER, {fetching: false, error: errorMessage})
					return
				}
				if (error.response.status >= 500) {
					errorMessage = 'Verify all services are up and registered'
				}
			}
			if (payload.type) {
				commit(payload.type, {rule: payload.rule, fetching: false, error: errorMessage, ...payload.payload})
			}
			reject(error)
		}))
}

export const getModule = (state, payload) => {
	if (!payload || !payload.module) return null
	if (payload.section && state[payload.section]) {
		return state[payload.section][payload.module]
	} else if (!payload.section) {
        return state[payload.module]
    }
}

export const FETCH_DATA_COUNT = 'FETCH_DATA_COUNT'
export const fetchDataCount = ({state, dispatch}, payload) => {
	let module = getModule(state, payload)
    if (!module) return
	const view = module.view

	let params = []

	if (view.query && view.query.filter) {
		params.push(`filter=${encodeURIComponent(view.query.filter)}`)
	}
	if (view.historical) {
		params.push(`history=${encodeURIComponent(view.historical)}`)
	}
	dispatch(REQUEST_API, {
		rule: `${payload.module}/count?${params.join('&')}`,
		type: UPDATE_DATA_COUNT,
		payload
	})
}

const createContentRequest = (state, payload) => {
    let module = getModule(state, payload)
    if (!module) return
	const view = module.view

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
		params.push(`filter=${encodeURIComponent(view.query.filter)}`)
	}
	if (view.historical) {
		params.push(`history=${encodeURIComponent(view.historical)}`)
	}
	// TODO: Not passing expressions because it might reach max URL size
	// if (view.query.expressions) {
	// 	params.push(`expressions=${encodeURI(JSON.stringify(view.query.expressions))}`)
	// }
	if (view.sort && view.sort.field) {
		params.push(`sort=${view.sort.field}`)
		params.push(`desc=${view.sort.desc? '1' : '0'}`)
	}
	if (payload.isRefresh) {
		params.push('is_refresh=1')
	}
	return params.join('&')
}

export const FETCH_DATA_CONTENT = 'FETCH_DATA_CONTENT'
export const fetchDataContent = ({state, dispatch}, payload) => {
	if (!payload.skip) {
		dispatch(FETCH_DATA_COUNT, { module: payload.module, section: payload.section})
	}
	return dispatch(REQUEST_API, {
		rule: `${payload.module}?${createContentRequest(state, payload)}`,
		type: UPDATE_DATA_CONTENT,
		payload
	})
}

export const FETCH_DATA_CONTENT_CSV = 'FETCH_DATA_CONTENT_CSV'
export const fetchDataContentCSV = ({state, dispatch}, payload) => {

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/csv?${createContentRequest(state, payload)}`,
		payload: {module: payload.module, skip: payload.skip}
	}).then((response) => {
        downloadFile('csv', response)
	})
}

export const downloadFile = (fileType, response)=>{
	let format = '';
	let reportType = '';
	switch (fileType) {
        case 'csv':
            format = 'csv';
            reportType = 'data';
            break
        case 'pdf':
            format = 'pdf';
            reportType = 'report';
            break
    }
    let blob = new Blob([response.data], { type: response.headers["content-type"]} )
    let link = document.getElementById('file-auto-download-link')
    link.href = window.URL.createObjectURL(blob)
    let now = new Date()
    let formattedDate = now.toLocaleDateString().replace(/\//g,'')
    let formattedTime = now.toLocaleTimeString().replace(/:/g,'')
    link.download = `axonius-${reportType}_${formattedDate}-${formattedTime}.${format}`
    link.click()
}

export const FETCH_DATA_VIEWS = 'FETCH_DATA_VIEWS'
export const fetchDataViews = ({state, dispatch}, payload) => {
	if (!getModule(state, payload)) return
    if (!payload.skip) payload.skip = 0
	if (!payload.limit) payload.limit = 1000

	let filter = `query_type=='${payload.type}'`
	if (payload.filter) {
		filter += ` and ${payload.filter}`
	}
	let param = `?limit=${payload.limit}&skip=${payload.skip}&filter=${encodeURI(filter)}`

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/views${param}`,
		type: UPDATE_DATA_VIEWS,
		payload: {module: payload.module, type: payload.type, skip: payload.skip}
	})
}

export const SAVE_DATA_VIEW = 'SAVE_DATA_VIEW'
export const saveDataView = ({state, dispatch, commit}, payload) => {
	if (!getModule(state, payload)) return
	payload.view = state[payload.module].view
	saveView({dispatch, commit}, payload)
}

export const SAVE_VIEW = 'SAVE_VIEW'
export const saveView = ({dispatch, commit}, payload) => {
	let viewObj = {
		name: payload.name, view: payload.view, query_type: 'saved'
	}
	if (payload.predefined) {
		viewObj.predefined = true
	}
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

export const REMOVE_DATA_VIEW = 'REMOVE_DATA_VIEW'
export const removeDataView = ({state, dispatch, commit}, payload) => {
	if (!getModule(state, payload) || !payload.ids || !payload.ids.length) return

	dispatch(REQUEST_API, {
		rule: `${payload.module}/views`,
		method: 'DELETE',
		data: payload.ids
	}).then((response) => {
		if (response.data !== '') {
			return
		}
		commit(UPDATE_REMOVED_DATA_VIEW, payload)
	})
}

export const FETCH_DATA_FIELDS = 'FETCH_DATA_FIELDS'
export const fetchDataFields = ({state, dispatch}, payload) => {
	if (!getModule(state, payload)) return
	dispatch(REQUEST_API, {
		rule: payload.module + '/fields',
		type: UPDATE_DATA_FIELDS,
		payload: {module: payload.module}
	})
}

export const FETCH_DATA_HYPERLINKS = 'FETCH_DATA_HYPERLINKS'
export const fetchDataHyperlinks = ({state, dispatch}, payload) => {
	if (!getModule(state, payload)) return
	dispatch(REQUEST_API, {
		rule: payload.module + '/hyperlinks',
		type: UPDATE_DATA_HYPERLINKS,
		payload: {module: payload.module}
	})
}

export const START_RESEARCH_PHASE = 'START_RESEARCH_PHASE'
export const startResearch = ({dispatch}) => {
    return dispatch(REQUEST_API, {
        rule: `research_phase`,
        method: 'POST'
    })
}

export const FETCH_DATA_LABELS = 'FETCH_DATA_LABELS'
export const fetchDataLabels = ({state, dispatch}, payload) => {
	if (!getModule(state, payload)) return
	dispatch(REQUEST_API, {
		rule: `${payload.module}/labels`,
		type: UPDATE_DATA_LABELS,
		payload: {module: payload.module}
	})
}

export const ADD_DATA_LABELS = 'ADD_DATA_LABELS'
export const addDataLabels = ({ state, dispatch }, payload) => {
	let moduleState = getModule(state, payload)
	if (!moduleState) return
	if (!payload.data || !payload.data.entities || !payload.data.labels || !payload.data.labels.length) {
		return
	}

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/labels?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'POST',
		data: payload.data,
        type: UPDATE_ADDED_DATA_LABELS,
        payload
	})
}

export const REMOVE_DATA_LABELS = 'REMOVE_DATA_LABELS'
export const removeDataLabels = ({ state, dispatch }, payload) => {
    let moduleState = getModule(state, payload)
    if (!moduleState) return
	if (!payload.data || !payload.data.entities || !payload.data.labels || !payload.data.labels.length) {
		return
	}

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/labels?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'DELETE',
		data: payload.data,
        type: UPDATE_REMOVED_DATA_LABELS,
        payload
	})
}

export const DISABLE_DATA = 'DISABLE_DATA'
export const disableData = ({state, dispatch}, payload) => {
    let moduleState = getModule(state, payload)
	if (!moduleState) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/disable?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'POST',
		data: payload.data
	})
}

export const DELETE_DATA = 'DELETE_DATA'
export const deleteData = ({state, dispatch}, payload) => {
    let moduleState = getModule(state, payload)
	if (!moduleState || !payload.data) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'DELETE',
		data: payload.data
	})
}

export const LINK_DATA = 'LINK_DATA'
export const linkData = ({state, dispatch}, payload) => {
    let moduleState = getModule(state, payload)
	if (!moduleState || !payload.data) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/manual_link?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'POST',
		data: payload.data
	})
}

export const UNLINK_DATA = 'UNLINK_DATA'
export const unlinkData = ({state, dispatch}, payload) => {
    let moduleState = getModule(state, payload)
	if (!moduleState || !payload.data) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/manual_unlink?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'POST',
		data: payload.data
	})
}

export const FETCH_DATA_BY_ID = 'FETCH_DATA_BY_ID'
export const fetchDataByID = ({state, dispatch}, payload) => {
	if (!getModule(state, payload)) return
	let rule = `${payload.module}/${payload.id}`
	if (payload.history) {
		rule += `?history=${encodeURIComponent(payload.history)}`
	}
	return dispatch(REQUEST_API, {
		rule: rule,
		type: UPDATE_DATA_BY_ID,
		payload
	})
}

export const SAVE_DATA_NOTE = 'SAVE_DATA_NOTE'
export const saveDataNote = ({state, dispatch}, payload) => {
    if (!getModule(state, payload)) return
    if (!payload.entityId) return
    let rule = `${payload.module}/${payload.entityId}/notes`
    let method = 'PUT'
    if (payload.noteId) {
        rule = `${rule}/${payload.noteId}`
        method = 'POST'
    }
    return dispatch(REQUEST_API, {
        rule, method,
		data: {
            note: payload.note
		},
        type: UPDATE_SAVED_DATA_NOTE,
        payload
    })
}

export const REMOVE_DATA_NOTE = 'REMOVE_DATA_NOTE'
export const removeDataNote = ({state, dispatch}, payload) => {
    if (!getModule(state, payload)) return
    if (!payload.entityId || !payload.noteIdList) return
    return dispatch(REQUEST_API, {
        rule: `${payload.module}/${payload.entityId}/notes`,
        method: 'DELETE',
        data: payload.noteIdList,
        type: UPDATE_REMOVED_DATA_NOTE,
		payload
    })
}

export const RUN_ACTION = 'RUN_ACTION'
export const runAction = ({state, dispatch}, payload) => {
	if (!payload || !payload.type || !payload.data) {
		return
	}
	return dispatch(REQUEST_API, {
		rule: `actions/${payload.type}?filter=${encodeURIComponent(state.devices.view.query.filter)}`,
		method: 'POST',
		data: payload.data
	})
}

export const STOP_RESEARCH_PHASE = 'STOP_RESEARCH_PHASE'
export const stopResearch = ({dispatch}) => {
    return dispatch(REQUEST_API, {
        rule: 'stop_research_phase',
        method: 'POST'
    })}

export const FETCH_SYSTEM_CONFIG = 'FETCH_SYSTEM_CONFIG'
export const fetchSystemConfig =({dispatch}) => {
    return dispatch(REQUEST_API, {
        rule: 'configuration',
        type: UPDATE_SYSTEM_CONFIG
    })
}

export const SAVE_CUSTOM_DATA = 'SAVE_CUSTOM_DATA'
export const saveCustomData = ({ state, dispatch }, payload) => {
	let module = getModule(state, payload)
    if (!module) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/custom?filter=${encodeURIComponent(module.view.query.filter)}`,
		method: 'POST',
		data: payload.data
	})
}