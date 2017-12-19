import axios from 'axios'
import Promise from 'promise'

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
export const requestApi = ({commit}, payload) => {
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
            resolve(response.data)
        })
        .catch((error) => {
            let userMessage = error.message
            if (error.response) {
                if (error.response.status >= 500) {
					userMessage = "Verify all services are up and registered"
				} else if (error.response.data.type === "PluginNotFoundException") {
                    userMessage = error.response.data.message
                }
            }
            if (payload.type) {
                commit(payload.type, {
                  fetching: false,
                  error: userMessage
                })
            }
            reject(error)
        }))
}
