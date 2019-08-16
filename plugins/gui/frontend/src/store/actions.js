import axios from 'axios'
import Promise from 'promise'

import { INIT_USER } from './modules/auth'
import {
	UPDATE_DATA, UPDATE_DATA_CONTENT, UPDATE_DATA_COUNT, UPDATE_DATA_COUNT_QUICK,
	ADD_DATA_VIEW, CHANGE_DATA_VIEW, UPDATE_DATA_FIELDS,
	UPDATE_DATA_LABELS, UPDATE_ADDED_DATA_LABELS, UPDATE_REMOVED_DATA_LABELS,
	SELECT_DATA_CURRENT, UPDATE_DATA_CURRENT,
	UPDATE_SAVED_DATA_NOTE, UPDATE_REMOVED_DATA_NOTE,
	UPDATE_SYSTEM_CONFIG, UPDATE_SYSTEM_EXPIRED, UPDATE_DATA_HYPERLINKS, UPDATE_CUSTOM_DATA, UPDATE_DATA_VIEW
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

let host = ''
if (process.env.NODE_ENV === 'development') {
	host = 'https://127.0.0.1'
}
export const currentHost = host
export const MAX_GET_SIZE = 2000
export const REQUEST_API = 'REQUEST_API'
export const requestApi = ({commit}, payload) => {
	if (!payload.rule) return

	if (payload.type) {
		commit(payload.type, {rule: payload.rule, fetching: true, error: '', ...payload.payload})
	}
	if (!payload.method) payload.method = 'GET'

	let request_config = {method: payload.method, url: `${host}/api/${payload.rule}`}
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
	return payload.module.split('/').reduce((moduleState, key) => {
		return moduleState[key]
	}, state)
}

export const FETCH_DATA_COUNT = 'FETCH_DATA_COUNT'
export const fetchDataCount = ({state, dispatch}, payload) => {
    let path = payload.endpoint || payload.module
	let module = getModule(state, payload)
    if (!module) return
	const view = module.view

    module.count.data = undefined

    // For now we support only /users and /devices 'big queries'
    if (view.query.filter.length > MAX_GET_SIZE && ['users', 'devices'].includes(path)) { 
        dispatch(REQUEST_API, {
            rule: `${path}/count`,
            type: UPDATE_DATA_COUNT,
            method: 'POST',
            data: {
                filter: view.query.filter,
                history: view.historical,
            },
            payload
        })

        dispatch(REQUEST_API, {
            rule: `${path}/count`,
            type: UPDATE_DATA_COUNT_QUICK,
            method: 'POST',
            data: {
                filter: view.query.filter,
                history: view.historical,
                quick: true
            },
            payload
        })
    } else {
        let params = []

        if (view.query && view.query.filter) {
            params.push(`filter=${encodeURIComponent(view.query.filter)}`)
        }
        if (view.historical) {
            params.push(`history=${encodeURIComponent(view.historical)}`)
        }

        dispatch(REQUEST_API, {
            rule: `${path}/count?${params.join('&')}`,
            type: UPDATE_DATA_COUNT,
            payload
        })

        params.push('quick=True')
        dispatch(REQUEST_API, {
            rule: `${path}/count?${params.join('&')}`,
            type: UPDATE_DATA_COUNT_QUICK,
            payload
        })
    }
}

const createPostContentRequest = (state, payload) => {
	let module = getModule(state, payload)
	if (!module) return ''
	const view = module.view

	let params = Object()

	if (payload.skip !== undefined) {
		params['skip'] = payload.skip
	}
	if (payload.limit !== undefined) {
		params['limit'] = payload.limit
	}
	if (view.fields && view.fields.length) {
        // fields is array, we want to foramt it as string
        // so we are using ${}
		params['fields'] = `${view.fields}`
	}
	if (view.query && view.query.filter) {
		params['filter'] = view.query.filter
	}
	if (view.historical) {
		params['history'] = view.historical
	}
	// TODO: Not passing expressions because it might reach max URL size
	// if (view.query.expressions) {
	// 	params.push(`expressions=${encodeURI(JSON.stringify(view.query.expressions))}`)
	// }

	if (view.sort && view.sort.field) {
		params['sort'] = view.sort.field
		params['desc'] = view.sort.desc? '1' : '0'
	}
	if (payload.isRefresh) {
		params['is_refresh'] = 1
	}
	return params
}

const createContentRequest = (state, payload) => {
    let params = createPostContentRequest(state, payload)
    let queryString = Object.keys(params).map(key => key + '=' + encodeURIComponent(params[key])).join('&')
    return queryString
}

export const FETCH_DATA_CONTENT = 'FETCH_DATA_CONTENT'
export const fetchDataContent = ({state, dispatch}, payload) => {
	let module = getModule(state, payload)
	let path = payload.endpoint || payload.module
	if (!module) return 
	const view = module.view

	if (!payload.skip && module.count !== undefined) {
		dispatch(FETCH_DATA_COUNT, { module: payload.module, endpoint: payload.endpoint})
	}

	if (!view) {
		return dispatch(REQUEST_API, {
			rule: path,
			type: UPDATE_DATA_CONTENT,
			payload
		})
	}

	if (view.query.filter.length > MAX_GET_SIZE && ['users', 'devices'].includes(path)) {
			return dispatch(REQUEST_API, {
					rule: path,
					type: UPDATE_DATA_CONTENT,
					method: 'POST',
					data: createPostContentRequest(state, payload),
					payload
			})
	}

	return dispatch(REQUEST_API, {
		rule: `${path}?${createContentRequest(state, payload)}`,
		type: UPDATE_DATA_CONTENT,
		payload
	})
}

export const FETCH_DATA_CONTENT_CSV = 'FETCH_DATA_CONTENT_CSV'
export const fetchDataContentCSV = ({state, dispatch}, payload) => {

	return dispatch(REQUEST_API, {
		rule: `${payload.endpoint || payload.module}/csv?${createContentRequest(state, payload)}`
	}).then((response) => {
        downloadFile('csv', response)
	})
}

export const downloadFile = (fileType, response) => {
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

export const downloadPdfReportFile = (name, response) => {
    let format = 'pdf';
    let blob = new Blob([response.data], { type: response.headers["content-type"]} )
    let link = document.getElementById('file-auto-download-link')
    link.href = window.URL.createObjectURL(blob)
    let now = new Date()
    let formattedDate = now.toLocaleDateString().replace(/\//g,'')
    let formattedTime = now.toLocaleTimeString().replace(/:/g,'')
    link.download = `${name}_${formattedDate}-${formattedTime}.${format}`
    link.click()
}

export const SAVE_DATA_VIEW = 'SAVE_DATA_VIEW'
export const saveDataView = ({state, dispatch, commit}, payload) => {
	if (!getModule(state, payload)) return
	payload.view = state[payload.module].view
	saveView({dispatch, commit}, payload)
}

export const SAVE_VIEW = 'SAVE_VIEW'
export const saveView = ({dispatch, commit}, payload) => {
	if (payload.uuid) {
		return dispatch(REQUEST_API, {
			rule: `${payload.module}/views/saved/${payload.uuid}`,
			data: {
				name: payload.name,
				view: payload.view
			},
			method: 'POST'
		}).then(() => {
			commit(CHANGE_DATA_VIEW, payload)
		})
	}
	let viewObj = {
		name: payload.name, view: {
			query: payload.view.query,
			fields: payload.view.fields,
			sort: payload.view.sort
		}
	}
	if (payload.predefined) {
		viewObj.predefined = true
	}
	dispatch(REQUEST_API, {
		rule: payload.module + '/views/saved',
		data: viewObj,
		method: 'POST'
	}).then((response) => {
		if (response.status === 200) {
			commit(ADD_DATA_VIEW, {
				module: payload.module, uuid: response.data, ...viewObj
			})
			if (!payload.predefined) {
				commit(UPDATE_DATA_VIEW, {module: payload.module, uuid: response.data})
			}
		}
	}).catch(console.log.bind(console))
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

export const FETCH_COMMON_LABELS = 'FETCH_COMMON_LABELS'
export const fetchCommonLabels = ({state, dispatch}, payload) => {
	let moduleState = getModule(state, payload)
	if (!moduleState) return
	return dispatch(REQUEST_API, {
		rule: `${payload.module}/labels/common?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'POST',
		data: payload.entities
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
	if (!moduleState || !payload.selection) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'DELETE',
		data: payload.selection
	}).then(response => {
		if (response.status === 200 && response.data === '') {
			dispatch(FETCH_DATA_CONTENT, payload)
		}
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

export const ENFORCE_DATA = 'ENFORCE_DATA'
export const enforceData = ({state, dispatch}, payload) => {
	let moduleState = getModule(state, payload)
	if (!moduleState || !payload.data) return

	return dispatch(REQUEST_API, {
		rule: `${payload.module}/enforce?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
		method: 'POST',
		data: payload.data
	}).then(() => {
		dispatch(FETCH_DATA_CONTENT, {
			module: 'tasks', skip: 0
		})
	})
}

export const FETCH_DATA_CURRENT = 'FETCH_DATA_CURRENT'
export const fetchDataCurrent = ({state, dispatch, commit}, payload) => {
	if (!getModule(state, payload)) return
	commit(SELECT_DATA_CURRENT, payload)

	let rule = `${payload.module}/${payload.id}`
	if (payload.history) {
		rule += `?history=${encodeURIComponent(payload.history)}`
	}
	return dispatch(REQUEST_API, {
		rule,
		type: UPDATE_DATA_CURRENT,
		payload: {
			module: `${payload.module}/current`
		}
	})
}

export const FETCH_DATA_CURRENT_TASKS = 'FETCH_DATA_CURRENT_TASKS'
export const fetchDataCurrentTasks = ({state, dispatch, commit}, payload) => {
	if (!getModule(state, payload)) return

	let rule = `${payload.module}/${payload.id}/tasks`
	if (payload.history) {
		rule += `?history=${encodeURIComponent(payload.history)}`
	}
	return dispatch(REQUEST_API, {
		rule,
		type: UPDATE_DATA,
		payload: {
			module: `${payload.module}/current/tasks`
		}
	})
}

export const SAVE_DATA_NOTE = 'SAVE_DATA_NOTE'
export const saveDataNote = ({ state, dispatch }, payload) => {
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
export const removeDataNote = ({ state, dispatch }, payload) => {
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

export const FETCH_SYSTEM_EXPIRED = 'FETCH_SYSTEM_EXPIRED'
export const fetchSystemExpired =({dispatch}) => {
	return dispatch(REQUEST_API, {
		rule: 'system/expired',
		type: UPDATE_SYSTEM_EXPIRED
	})
}

export const SAVE_CUSTOM_DATA = 'SAVE_CUSTOM_DATA'
export const saveCustomData = ({ state, dispatch }, payload) => {
	let module = getModule(state, payload)
    if (!module) return

	let fieldData = payload.data.reduce((map, item) => {
		map[item.title || item.name] = item.value
		return map
	}, {})
	fieldData.id = 'unique'
	return dispatch(REQUEST_API, {
		rule: `${payload.module}/custom?filter=${encodeURIComponent(module.view.query.filter)}`,
		method: 'POST',
		data: {
			selection: payload.selection,
			data: fieldData
		},
		type: UPDATE_CUSTOM_DATA,
		payload
	})
}
