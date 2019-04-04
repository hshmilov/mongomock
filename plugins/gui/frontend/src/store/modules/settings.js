import {REQUEST_API} from '../actions'

export const SAVE_PLUGIN_CONFIG = 'SAVE_PLUGIN_CONFIG'
export const LOAD_PLUGIN_CONFIG = 'LOAD_PLUGIN_CONFIG'
export const CHANGE_PLUGIN_CONFIG = 'CHANGE_PLUGIN_CONFIG'

export const FETCH_MAINTENANCE_CONFIG = 'FETCH_MAINTENANCE_CONFIG'
export const UPDATE_MAINTENANCE_CONFIG = 'UPDATE_MAINTENANCE_CONFIG'
export const SAVE_MAINTENANCE_CONFIG = 'SAVE_MAINTENANCE_CONFIG'
export const START_MAINTENANCE_CONFIG = 'START_MAINTENANCE_CONFIG'
export const STOP_MAINTENANCE_CONFIG = 'STOP_MAINTENANCE_CONFIG'

export const settings = {
    state: {
        configurable: {},
        advanced: {
            maintenance: {
                provision: true,
                analytics: true,
                troubleshooting: true,
                timeout: null
            }
        }
    },
    mutations: {
        [CHANGE_PLUGIN_CONFIG](state, payload) {
            if (!state.configurable[payload.pluginId]) {
                state.configurable[payload.pluginId] = {}
            }
            if (!state.configurable[payload.pluginId][payload.configName]) {
                state.configurable[payload.pluginId][payload.configName] = {}
            }
            state.configurable = {
                ...state.configurable,
                [payload.pluginId]: {
                    ...state.configurable[payload.pluginId],
                    [payload.configName]: {
                        fetching: payload.fetching, error: payload.error,
                        config: payload.data ?
                          payload.data.config :
                          state.configurable[payload.pluginId][payload.configName].config,
                        schema: payload.data ?
                          payload.data.schema :
                          state.configurable[payload.pluginId][payload.configName].schema
                    }
                }
            }
        },
        [UPDATE_MAINTENANCE_CONFIG](state, payload) {
            if (payload.data) {
                state.advanced.maintenance = {
                    ...state.advanced.maintenance, ...payload.data
                }
            }
        }
    },
    actions: {
        [SAVE_PLUGIN_CONFIG]({dispatch, commit}, payload) {
            /*
                Call API to save given config to adapters by the given adapters unique name
             */
            if (!payload || !payload.pluginId || !payload.configName) {
                return
            }
            let rule = `plugins/configs/${payload.pluginId}/${payload.configName}`
            return dispatch(REQUEST_API, {
                rule,
                method: 'POST',
                data: payload.config
            }).then(response => {
                if (response.status === 200) {
                    commit(CHANGE_PLUGIN_CONFIG, {
                        pluginId: payload.pluginId,
                        configName: payload.configName,
                        config: payload.config
                    })

                }
                return response
            })
        },
        [LOAD_PLUGIN_CONFIG]({dispatch, commit}, payload) {
            /*
                Call API to save given config to adapters by the given adapters unique name
             */
            if (!payload || !payload.pluginId || !payload.configName) return

            let rule = `plugins/configs/${payload.pluginId}/${payload.configName}`
            return dispatch(REQUEST_API, {
                rule,
                type: CHANGE_PLUGIN_CONFIG,
                payload
            })
        },
        [FETCH_MAINTENANCE_CONFIG]({dispatch}) {
            return dispatch(REQUEST_API, {
                rule: 'config/maintenance',
                type: UPDATE_MAINTENANCE_CONFIG
            })
        },
        [SAVE_MAINTENANCE_CONFIG]({dispatch, commit}, payload) {
            if (payload.provision) {
                payload = { ...payload,
                    analytics: true, troubleshooting: true, timeout: null
                }
            }
            return dispatch(REQUEST_API, {
                rule: 'config/maintenance',
                method: 'POST',
                data: payload
            }).then(response => {
                if (response.status === 200) {
                    commit(UPDATE_MAINTENANCE_CONFIG, {
                        data: payload
                    })
                }
            })
        },
        [START_MAINTENANCE_CONFIG]({dispatch, commit}, payload) {
            return dispatch(REQUEST_API, {
                rule: 'config/maintenance',
                method: 'PUT',
                data: payload
            }).then(response => {
                if (response.status === 200 && response.data) {
                    commit(UPDATE_MAINTENANCE_CONFIG, {
                        data: response.data
                    })
                }
            })
        },
        [STOP_MAINTENANCE_CONFIG]({dispatch, commit}) {
            return dispatch(REQUEST_API, {
                rule: 'config/maintenance',
                method: 'DELETE'
            }).then(response => {
                if (response.status === 200) {
                    commit(UPDATE_MAINTENANCE_CONFIG, {
                        data: {
                            timeout: null
                        }
                    })
                }
            })
        }
    }
}
