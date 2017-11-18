/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_FIELDS = 'FETCH_FIELDS'
export const UPDATE_FIELDS = 'UPDATE_FIELDS'
export const FETCH_TAGS = 'FETCH_TAGS'
export const UPDATE_TAGS = 'UPDATE_TAGS'
export const UPDATE_DEVICE_TAGS = 'UPDATE_DEVICE_TAGS'
export const SAVE_DEVICE_TAGS = 'SAVE_DEVICE_TAGS'
export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'

export const device = {
	state: {
		/* Devices according to some query performed by user, updating by request */
		deviceList: {fetching: false, data: [], error: ''},

		/* Info of one device that was requested */
		deviceDetails: {fetching: false, data: {}, error: ''},

		/* Configurations specific for devices */
		fields: [
			{
				path: 'adapters', name: 'Adapters', default: true, selected: true, type: 'image-list', querySchema: {
				type: 'multiple-select',
				options: [
					{name: 'Active Dirsectory', path: 'ad_adapter'},
					{name: 'ESX', path: 'esx_adapter'},
					{name: 'CheckPoint', path: 'checkpoint_adapter'},
					{name: 'QCore', path: 'qcore_adapter'},
					{name: 'Splunk', path: 'splunk_adapter'}
				]
			}
			},
			{
				path: 'pretty_id', name: 'Axonius Name', selected: true, querySchema: {
				type: 'text'
			}
			},
			{
				path: 'name', name: 'Host Name', selected: true, querySchema: {
				type: 'text'
			}
			},
			{path: 'IP', name: 'IP Address', selected: true},
			{
				path: 'OS.type', name: 'Operating System', selected: true, querySchema: {
				type: 'text'
			}
			},
			{
				path: 'tags', name: 'Tags', default: true, selected: true, type: 'tag-list', querySchema: {
				type: 'multiple-select',
				options: []
			}
			}
		],
		tagList: {fetching: false, data: [], error: ''},
		adapterNames: {
			'ad_adapter': 'Active Directory',
			'esx_adapter': 'ESX',
			'checkpoint_adapter': 'CheckPoint',
			'qcore_adapter': 'QCore',
			'splunk_adapter': 'Splunk'
		}
	},
	getters: {
		deviceNames (state) {
			return state.deviceList.data.map(function (device) {
				return device['name']
			})
		}
	},
	mutations: {
		[ RESTART_DEVICES ] (state) {
			state.deviceList.data = []
		},
		[ UPDATE_DEVICES ] (state, payload) {
			/* Freshly fetched devices are added to currently stored devices */
			state.deviceList.fetching = payload.fetching
			if (payload.data) {
				let processedData = []
				payload.data.forEach(function (device) {
					let processedDevice = { 'id': device['internal_axon_id'] }
					processedDevice['adapters'] = Object.keys(device.adapters)
					state.fields.forEach(function (field) {
						if (!field.default) {
							let data = device.adapters
							if (field.path.indexOf('data') === -1) {
								data = data[processedDevice.adapters[0]].data
							}
							let pathParts = field.path.split(".")
							pathParts.forEach(function(part) {
								if (data === undefined) { return }
								data = data[part]
							})
							processedDevice[field.path] = data
						}
					})
					processedDevice['tags'] = device.tags
					processedData.push(processedDevice)
				})
				state.deviceList.data = [...state.deviceList.data, ...processedData]
			}
			if (payload.error) {
				state.deviceList.error = payload.error
			}
		},
		[ UPDATE_FIELDS ] (state, payload) {
			if (payload.data) {
				payload.data.forEach(function(field) {
					let fieldParts = field.split('.')
					state.fields.push({
						path: field,
						name: state.adapterNames[fieldParts[0]] + ': ' + fieldParts[3],
						querySchema: {
							type: 'text'
						}
					})
				})
			}
		},
		[ UPDATE_TAGS ] (state, payload) {
			state.tagList.fetching = payload.fetching
			if (payload.data) {
				state.tagList.data = payload.data.map(function(tag) {
					return {name: tag, path: tag}
				})
				state.fields.forEach(function(field) {
					if (field.path === 'tags') {
						field.querySchema.options = state.tagList.data
					}
				})
			}
			if (payload.error) {
				state.tagList.error = payload.error
			}
		},
		[ UPDATE_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data.forEach(function (device) {
				if (payload.devices.indexOf(device['id']) > -1) {
					device['tags'] = payload.tags
				}
			})
			let tags = state.tagList.data.map(function(tag) {
				return tag.path
			})
			payload.tags.forEach(function (tag) {
				if (tags.indexOf(tag) === -1) {
					state.tagList.data.push({name: tag, path: tag})
				}
			})
		},
		[ UPDATE_DEVICE ] (state, payload) {
			state.deviceDetails.fetching = payload.fetching
			if (payload.data) {
				state.deviceDetails.data = {
					adapters: Object.keys(payload.data.adapters),
					tags: payload.data.tags
				}
				let adapterData = payload.data.adapters[state.deviceDetails.data.adapters[0]]
				state.deviceDetails.name = adapterData.data.name
				state.deviceDetails.IP = adapterData.data.IP
			}
			if (payload.error) {
				state.deviceDetails.error = payload.error
			}
		}
	},
	actions: {
		[ FETCH_DEVICES ] ({dispatch, commit}, payload) {
			/* Fetch list of devices for requested page and filtering */
			if (!payload.skip) { payload.skip = 0 }
			/* Getting first page - empty table */
			if (payload.skip === 0) { commit(RESTART_DEVICES) }
			let param = `?limit=${payload.limit}&skip=${payload.skip}`
			if (payload.filter && Object.keys(payload.filter).length) {
				param += `&filter=${JSON.stringify(payload.filter)}`
			}
			dispatch(REQUEST_API, {
				rule: `api/devices${param}`,
				type: UPDATE_DEVICES
			})
		},
		[ FETCH_DEVICE ] ({dispatch}, deviceId) {
			/* Fetch a single device according to requested id */
			if (!deviceId) { return }
			dispatch(REQUEST_API, {
				rule: `api/devices/${deviceId}`,
				type: UPDATE_DEVICE
			})
		},
		[ FETCH_FIELDS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `api/fields`,
				type: UPDATE_FIELDS
			})
		},
		[ FETCH_TAGS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `api/tags`,
				type: UPDATE_TAGS
			})
		},
		[ SAVE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			commit(UPDATE_DEVICE_TAGS, payload)
			payload.devices.forEach(function(device) {
				dispatch(REQUEST_API, {
					rule: `api/devices/${device}`,
					method: 'POST',
					data: { tags: payload.tags }
				})
			})
		}
	}
}