import { REQUEST_API } from '../actions'

export const FETCH_PLUGINS = 'FETCH_PLUGINS'
export const UPDATE_PLUGINS = 'UPDATE_PLUGINS'
export const FETCH_PLUGIN = 'FETCH_PLUGIN'
export const UPDATE_PLUGIN = 'UPDATE_PLUGIN'

export const START_PLUGIN = 'START_PLUGIN'
export const UPDATE_PLUGIN_START = 'UPDATE_PLUGIN_START'
export const STOP_PLUGIN = 'STOP_PLUGIN'
export const UPDATE_PLUGIN_STOP = 'UPDATE_PLUGIN_STOP'

export const pluginStaticData = {
	'dns_conflicts_plugin': {
		name: 'Conflicting IP',
		description: 'The Conflicting IP plugin uses data from Active Directory and other DNS servers to compare the hostnames of devices to identify conflicting IP addresses.'
	},
	'static_correlator': {
		name: 'Static Correlator',
		description: 'The Static Correlator plugin compares values across managed devices to discover instances of the same device.'
	},
	'careful_execution_correlator_plugin': {
		name: 'Execution Correlator',
		description: 'The Execution Correlator plugin executes commands on different adapters and compares the output to identify unique devices.'
	}
}

export const plugin = {
	state: {
		pluginList: {fetching: false, data: [], error: ''},
		fields: [
			{path: 'unique_plugin_name', name: '', hidden: true},
			{path: 'plugin_name', name: 'Name', type: 'status-icon-logo-text'},
			{path: 'description', name: 'Description'},
			{path: 'status', name: '', hidden: true},
			{path: 'state', name: 'Status'}
		],
		currentPlugin: {data: {state: 'Disabled', results: []}, fetching: false, error: ''}

	},
	getters: {},
	mutations: {
		[ UPDATE_PLUGINS ] (state, payload) {
			/*
				Called once before request to server for getting plugins, to notify that it is being fetched
				Called next after request either fails or succeeds and updates error or data accordingly.
				The data is modified to include the name and description, if found in the pluginStaticData.
				(Will be removed when plugins will return their own static data)
			 */
			state.pluginList.fetching = payload.fetching
			state.pluginList.error = payload.error
			if (payload.data) {
				state.pluginList.data = payload.data.map((plugin) => {
					let name = plugin.plugin_name
					let description = ''
					if (pluginStaticData[plugin.plugin_name]) {
						name = pluginStaticData[plugin.plugin_name].name
						description = pluginStaticData[plugin.plugin_name].description
					}
					return {
						id: plugin.unique_plugin_name,
						plugin_name: {
							text: name,
							logo: plugin.plugin_name,
							status: plugin.status
						},
						state: plugin.state,
						description: description,
						startable: (plugin.status !== 'error' && plugin.state === 'Disabled'),
						stoppable: (plugin.status !== 'error' && (plugin.state === 'Scheduled' || plugin.state === 'InProgress')),
						configurable: plugin.plugin_name === 'dns_conflicts_plugin'
					}
				})
			}
		},
		[ UPDATE_PLUGIN ] (state, payload) {
			/*
				Called once before request to server for getting plugins, to notify that it is being fetched
				Called next after request either fails or succeeds and updates error or data accordingly
			 */
			state.pluginList.fetching = payload.fetching
			state.pluginList.error = payload.error
			if (payload.data) {
				state.currentPlugin.data = {
					...payload.data,
					results: payload.data.results.map((result) => {
						let processedResult = {
							uuid: result.uuid,
							conflicts: [],
							adapters: result.adapters
						}
						let tag = result.tags.filter((tag) => {
							return tag.tagname === 'IP_CONFLICT'
						})

						if (tag && tag.length && tag[0].tagvalue) {
							let conflictMap = JSON.parse(tag[0].tagvalue)
							processedResult.conflicts = Object.keys(conflictMap).map((conflictIP) => {
								return {ip: conflictIP, server: conflictMap[conflictIP]}
							})
							// TODO Take only adapters relevant according to tag's 'associated_adapter_devices'
						}
						return processedResult
					}).filter((result) => {
						return result.conflicts.length > 0
					})
				}
			}
		},
		[ UPDATE_PLUGIN_START ] (state, pluginId) {
			state.pluginList.data.forEach((plugin) => {
				if (plugin.id === pluginId) {
					plugin.state = 'StartingUp'
					plugin.startable = false
					plugin.stoppable = false
					plugin.plugin_name.status = 'success'
				}
			})
			if (state.currentPlugin.data.plugin_unique_name === pluginId) {
				state.currentPlugin.data.state = 'Scheduled'
			}
		},
		[ UPDATE_PLUGIN_STOP ] (state, pluginId) {
			state.pluginList.data.forEach((plugin) => {
				if (plugin.id === pluginId) {
					plugin.state = 'ShuttingDown'
					plugin.startable = false
					plugin.stoppable = false
					plugin.plugin_name.status = 'warning'
				}
			})
			if (state.currentPlugin.data.plugin_unique_name === pluginId) {
				state.currentPlugin.data.state = 'Disabled'
			}
		}
	},
	actions: {
		[ FETCH_PLUGINS ] ({dispatch}, payload) {
			/*
				Getting plugins answering the filter, if given
			 */
			let param = ''
			if (payload && payload.filter) {
				param = `?filter=${JSON.stringify(payload.filter)}`
			}
			return dispatch(REQUEST_API, {
				rule: `/api/plugins${param}`,
				type: UPDATE_PLUGINS
			})
		},
		[ FETCH_PLUGIN ] ({dispatch}, pluginId) {
			/*
				Fetching plugin data according to given id - unique_plugin_name value
			 */
			if (!pluginId) { return }
			dispatch(REQUEST_API, {
				rule: `/api/plugins/${pluginId}`,
				type: UPDATE_PLUGIN
			})
		},
		[ START_PLUGIN ] ({dispatch, commit}, pluginId) {
			/*
				Request from given plugin to start doing its magic
			 */
			if (!pluginId) { return }
			dispatch(REQUEST_API, {
				rule: `/api/plugins/${pluginId}/start`
			}).then((response) => {
				if (response !== '') {
					return
				}
				commit(UPDATE_PLUGIN_START, pluginId)
			})
		},
		[ STOP_PLUGIN ] ({dispatch, commit}, pluginId) {
			/*
				Request from given plugin to pause doing its magic
			 */
			if (!pluginId) { return }
			dispatch(REQUEST_API, {
				rule: `/api/plugins/${pluginId}/stop`
			}).then((response) => {
				if (response !== '') {
					return
				}
				commit(UPDATE_PLUGIN_STOP, pluginId)
			})
		}
	}
}