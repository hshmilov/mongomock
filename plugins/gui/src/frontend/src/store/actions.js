import axios from 'axios'
import Promise from 'promise'

import { INIT_USER, SET_USER } from './modules/user'

/*
    A generic wrapper for requests to server.
    Before request, performs given mutation to initialize error and indicate fetching in process,
    After request, performs given mutation with data received or error thrown, accordingly

    @param {commit} - Vue action mechanism provides this
    @param payload - An object containing: {
        method: HTTP method for the request [defaulted GET]
        rule: Entry in the API to call, including request parameters, if needed
        data: Object with data, for HTTP methods that allow sending it, if needed,
        type: Mutation type to call
    }
 */
export const REQUEST_API = 'REQUEST_API'
export const requestApi = ({dispatch, commit}, payload) => {
    if (!payload.rule) {
        return
    }
    if (payload.type) {
        commit(payload.type, {
            fetching: true,
            error: ''
        })
    }
    if (!payload.method) { payload.method = 'GET' }
    let request_config = {
        method: payload.method,
        url: payload.rule
    }
    if (payload.data) {
        request_config['data'] = payload.data
    }
    return new Promise((resolve, reject) => axios(request_config)
        .then((response) => {
            if (payload.type) {
                commit(payload.type, {
                  fetching: false,
                  data: response.data
                })
            }
            resolve(response)
        })
        .catch((error) => {
			let errorMessage = error.response.data.message
			if (error.response.status === 401) {
				commit(INIT_USER, { fetching: false, error: errorMessage })
				return
			}
            if (error.response.status >= 500) {
                errorMessage = "Verify all services are up and registered"
            }
            if (payload.type) {
                commit(payload.type, {
                  fetching: false,
                  error: errorMessage
                })
            }
            reject(error)
        }))
}
