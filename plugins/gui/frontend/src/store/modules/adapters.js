import {REQUEST_API} from '../actions'
import { pluginMeta } from '../../constants/plugin_meta.js'

export const FETCH_ADAPTERS = 'FETCH_ADAPTERS'
export const UPDATE_ADAPTERS = 'UPDATE_ADAPTERS'
export const UPDATE_CURRENT_ADAPTER = 'UPDATE_CURRENT_ADAPTER'

export const SAVE_ADAPTER_SERVER = 'SAVE_ADAPTER_SERVER'
export const TEST_ADAPTER_SERVER = 'TEST_ADAPTER_SERVER'
export const UPDATE_ADAPTER_SERVER = 'UPDATE_ADAPTER_SERVER'
export const ARCHIVE_SERVER = 'ARCHIVE_SERVER'
export const REMOVE_SERVER = 'REMOVE_SERVER'

export const UPDATE_ADAPTER_STATUS = 'UPDATE_ADAPTER_STATUS'


export const adapters = {
	state: {
		/* All adapters */
		adapterList: {
			fetching: false, data: [], error: ''
		},

		currentAdapter: null
	},
	mutations: {
		[ UPDATE_ADAPTERS ] (state, payload) {
			/*
				Called first before API request for adapters, in order to update state to fetching
				Called again after API call returns with either error or result controls, that is added to adapters list
			 */
			state.adapterList.fetching = payload.fetching
			if (payload.data) {
				state.adapterList.data = []
				for (let pluginName in payload.data) {
					let current_plugin_data = payload.data[pluginName]
                    let pluginTitle = pluginName
                    let pluginDescription = ''
                    if (pluginMeta[pluginName]) {
                        pluginDescription = pluginMeta[pluginName].description
                        pluginTitle = pluginMeta[pluginName].title
                    }
                    let status = ''
					current_plugin_data.forEach((unique_adapter) => {
						if (unique_adapter.status === "error") {
							status = "warning"
						}
						else if (unique_adapter.status !== "" &&  status !== "warning") {
							status = unique_adapter.status
						}
					})
                    state.adapterList.data.push({
                        ...current_plugin_data,
                        id: pluginName,
                        title: pluginTitle,
						status: status,
                        description: pluginDescription,
                        supported_features: current_plugin_data[0].supported_features
                    })
				}
				state.adapterList.data.sort((first, second) => {
					// Sort by adapters plugin name (the one that is shown in the gui).
					let firstText = first.title.toLowerCase()
					let secondText = second.title.toLowerCase()
					if (firstText < secondText) return -1
					if (firstText > secondText) return 1
					return 0
				})
				if (state.currentAdapter && state.currentAdapter.id) {
					state.currentAdapter = state.adapterList.data.find(
						adapter => adapter.id === state.currentAdapter.id)
				}
			}
			if (payload.error) {
				state.adapterList.error = payload.error
			}
		},
		[ UPDATE_CURRENT_ADAPTER ] (state, adapterId) {
			state.currentAdapter = state.adapterList.data.find(adapter => adapter.id === adapterId)
		},
		[ UPDATE_ADAPTER_SERVER ] (state, payload) {
			if (!payload.uuid) {
                Object.values(state.currentAdapter).filter(field => (field.clients && field.node_id === payload.client_config.instanceName))[0].clients.push(payload)
				return
			}
            Object.values(state.currentAdapter).filter(field => (field.clients)).forEach((adapter) => {
                adapter.clients.forEach((client) => {
                    if (client.uuid === payload.uuid) {
                        client = payload
                    }
                })
            })
		},
		[ REMOVE_SERVER ] (state, serverId) {
			Object.values(state.currentAdapter).filter(field => (field.clients)).forEach((adapter) => {
				adapter.clients = adapter.clients.filter(currentClient => currentClient.uuid !== serverId)
				})
		},
		[ UPDATE_ADAPTER_STATUS ] (state, adapterId) {
			state.adapterList.data = state.adapterList.data.map((item) => {
				if (item.id !== adapterId) return item
				return { ...item, status: 'warning' }
			})
		}
	},
	actions: {
		[ FETCH_ADAPTERS ] ({dispatch}, payload) {
			/*
				Fetch all adapters, according to given filter
			 */
			let param = ''
			if (payload && payload.filter) {
				param = `?filter=${JSON.stringify(payload.filter)}`
			}
			return dispatch(REQUEST_API, {
				rule: `adapters${param}`,
				type: UPDATE_ADAPTERS
			})
		},
		[ SAVE_ADAPTER_SERVER ] ({dispatch, commit}, payload) {
			/*
				Call API to save given server controls to adapters by the given adapters id,
				either adding a new server or updating and existing one, if id is provided with the controls
			 */
			if (!payload || !payload.adapterId || !payload.serverData) { return }
			let rule = `adapters/${payload.adapterId}/clients`
			if (payload.uuid !== 'new') {
				rule += '/' + payload.uuid
			}
			commit(UPDATE_ADAPTER_SERVER, {
				client_config: payload.serverData,
				uuid: (payload.uuid !== 'new') ? payload.uuid: '',
				status: 'warning'
			})
			commit(UPDATE_ADAPTER_STATUS, payload.adapterId)

			return dispatch(REQUEST_API, {
				rule: rule,
				method: 'PUT',
				data: payload.serverData
			})
		},
        [ TEST_ADAPTER_SERVER ] ({dispatch}, payload) {
            /*
                Call API to test connectivity to given server controls to adapters by the given adapters id,
                either adding a new server or updating and existing one, if id is provided with the controls
             */
            if (!payload || !payload.adapterId || !payload.serverData) { return }
            let rule = `adapters/${payload.adapterId}/clients`

            return dispatch(REQUEST_API, {
                rule: rule,
                method: 'post',
                data: payload.serverData
            })
        },
		[ ARCHIVE_SERVER ] ({dispatch, commit}, payload) {
			if (!payload.adapterId || !payload.serverId) { return }
            let param = ''
            if (payload.deleteEntities) {
				param = '?deleteEntities=True'
			}
			dispatch(REQUEST_API, {
				rule: `adapters/${payload.adapterId}/clients/${payload.serverId}${param}`,
				method: 'DELETE',
				data: {instanceName: payload.nodeId}
			}).then((response) => {
				if (response.data !== '') {
					return
				}
				commit(REMOVE_SERVER, payload.serverId)
			})
		}
	}
}
