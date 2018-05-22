import {REQUEST_API} from '../actions'

export const SAVE_PLUGIN_CONFIG = 'SAVE_PLUGIN_CONFIG'
export const LOAD_PLUGIN_CONFIG = 'LOAD_PLUGIN_CONFIG'
export const CHANGE_PLUGIN_CONFIG = 'CHANGE_PLUGIN_CONFIG'

export const configurable = {
    state: {},
    getters: {},
    mutations: {
        [CHANGE_PLUGIN_CONFIG](state, payload) {
            if (!state[payload.pluginId]) state[payload.pluginId] = {}
            state[payload.pluginId][payload.configName] = {...state[payload.pluginId][payload.configName],
                config: payload.config}
            if (payload.schema) {
                state[payload.pluginId][payload.configName].schema = payload.schema
            }
            this.state.configurable = {...this.state.configurable}
        }
    },
    actions: {
        [SAVE_PLUGIN_CONFIG]({dispatch}, payload) {
            /*
                Call API to save given config to adapter by the given adapter unique name
             */
            if (!payload || !payload.pluginId || !payload.configName) {
                return
            }
            let rule = `plugins/configs/${payload.pluginId}/${payload.configName}`

            return dispatch(REQUEST_API, {
                rule: rule,
                method: 'POST',
                data: payload.config
            })
        },
        [LOAD_PLUGIN_CONFIG]({dispatch, commit}, payload) {
            /*
                Call API to save given config to adapter by the given adapter unique name
             */
            if (!payload || !payload.pluginId || !payload.configName) {
                return
            }
            var pluginId = payload.pluginId
            var configName = payload.configName
            let rule = `plugins/configs/${pluginId}/${configName}`
            return dispatch(REQUEST_API, {
                rule: rule,
            }).then(response => {
                if (response.data) {
                    commit(CHANGE_PLUGIN_CONFIG, {
                        pluginId: pluginId,
                        configName: configName,
                        config: response.data.config,
                        schema: response.data.schema
                    })
                }
            })
        }
    }
}
