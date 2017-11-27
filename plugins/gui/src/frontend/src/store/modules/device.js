/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_UNIQUE_FIELDS = 'FETCH_UNIQUE_FIELDS'
export const UPDATE_UNIQUE_FIELDS = 'UPDATE_UNIQUE_FIELDS'
export const FETCH_TAGS = 'FETCH_TAGS'
export const UPDATE_TAGS = 'UPDATE_TAGS'
export const UPDATE_DEVICE_TAGS = 'UPDATE_DEVICE_TAGS'
export const SAVE_DEVICE_TAGS = 'SAVE_DEVICE_TAGS'
export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'

export const decomposeFieldPath = (data, fieldPath) => {
	/*
		Find ultimate value of data, matching given field path, by recursively drilling into the dictionary,
		until path exhausted or reached undefined.
		Arrays along the way will be traversed so that final value is the list of all found values
	 */
	if (!data || typeof(data) === 'string' || (Array.isArray(data) && (!data.length || typeof(data[0]) === 'string'))) {
		return data
	}
	let nextFieldPath = fieldPath.substring(fieldPath.indexOf('.') + 1)
	if (Array.isArray(data)) {
		let aggregatedValues = []
		data.forEach((item) => {
			let foundValue = decomposeFieldPath(item, nextFieldPath)
			if (Array.isArray(foundValue)) {
				aggregatedValues = aggregatedValues.concat(foundValue)
			} else {
				aggregatedValues = aggregatedValues.push(foundValue)
			}
		})
		return aggregatedValues
	}
	if (fieldPath.indexOf('.') === -1) {
		return data[fieldPath]
	}
	let currentFieldPath = fieldPath.substring(0, fieldPath.indexOf('.'))
	return decomposeFieldPath(data[currentFieldPath], nextFieldPath)
}

export const findValue = (field, data) => {
	let value = undefined
	let dataIndex = 0
	let fieldPathAdapters = field.path.replace(/adapters\./, '')
	while (!value && dataIndex < data.length) {
		value = decomposeFieldPath(data[dataIndex], fieldPathAdapters)
		dataIndex++
	}
	return value
}

export const device = {
	state: {
		/* Devices according to some query performed by user, updating by request */
		deviceList: {fetching: false, data: [], error: ''},

		/* Info of one device that was requested */
		deviceDetails: {fetching: false, data: {}, error: ''},

		/* Configurations specific for devices */
		fields: {
			common: [
				{
					path: 'adapters.plugin_name', name: 'Adapters', selected: true, type: 'image-list', control: 'multiple-select',
					options: [
						{name: 'Active Dirsectory', path: 'ad_adapter'},
						{name: 'ESX', path: 'esx_adapter'},
						{name: 'AWS', path: 'aws_adapter'},
						{name: 'CheckPoint', path: 'checkpoint_adapter'},
						{name: 'QCore', path: 'qcore_adapter'},
						{name: 'Splunk', path: 'splunk_adapter'}
					]
				},
				{path: 'adapters.data.pretty_id', name: 'Axonius Name', selected: true, control: 'text'},
				{path: 'adapters.data.name', name: 'Host Name', selected: true, control: 'text'},
				{path: 'adapters.data.network_interfaces.public_ip', name: 'IP Address', selected: true, type: 'list'},
				{path: 'adapters.data.OS.type', name: 'Operating System', selected: true, control: 'text'},
				{path: 'tags', name: 'Tags', selected: true, type: 'tag-list', control: 'multiple-select', options: []}
			],
			unique: []
		},
		tagList: {fetching: false, data: [], error: ''}
	},
	getters: {},
	mutations: {
		[ RESTART_DEVICES ] (state) {
			state.deviceList.data = []
		},
		[ UPDATE_DEVICES ] (state, payload) {
			/* Freshly fetched devices are added to currently stored devices */
			state.deviceList.fetching = payload.fetching
			if (payload.data) {
				let processedData = []
				payload.data.forEach((device) => {
					if (!device.adapters || !device.adapters.length) { return }
					let processedDevice = {'id': device['internal_axon_id']}
					processedDevice['adapters.plugin_name'] = device.adapters.map((adapter) => {
						return adapter.plugin_name
					})
					processedDevice.tags = device.tags.map((tag) => {
						return tag.tagname
					})
					state.fields.common.forEach((field) => {
						if (field.path === 'adapters.plugin_name' ||  field.path === 'tags') { return }
						let value = findValue(field, device.adapters)
						if (value) { processedDevice[field.path] = value }
					})
					state.fields.unique.forEach((field) => {
						let value = findValue(field, device.adapters)
						if (value) { findValue(field, device.adapters) }
					})
					processedData.push(processedDevice)
				})
				state.deviceList.data = [...state.deviceList.data, ...processedData]
			}
			if (payload.error) {
				state.deviceList.error = payload.error
			}
		},
		[ UPDATE_UNIQUE_FIELDS ] (state, payload) {
			if (payload.data) {
				payload.data.forEach(function (field) {
					let fieldParts = field.split('.')
					let fieldName = fieldParts.splice(4).join(".")
					state.fields.unique.push({
						path: field, name: fieldParts[1].split('_')[0] + ': ' + fieldName, control: 'text'
					})
				})
			}
		},
		[ UPDATE_TAGS ] (state, payload) {
			state.tagList.fetching = payload.fetching
			if (payload.data) {
				state.tagList.data = payload.data.map(function (tag) {
					return {name: tag, path: tag}
				})
				state.fields.common.forEach(function (field) {
					if (field.path === 'tags') {
						field.options = state.tagList.data
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
			let tags = state.tagList.data.map(function (tag) {
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
			if (payload.fields && payload.fields.length) {
				param += `&fields=${payload.fields}`
			}
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
		[ FETCH_UNIQUE_FIELDS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `api/devices/fields`,
				type: UPDATE_UNIQUE_FIELDS
			})
		},
		[ FETCH_TAGS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `api/devices/tags`,
				type: UPDATE_TAGS
			})
		},
		[ SAVE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			commit(UPDATE_DEVICE_TAGS, payload)
			payload.devices.forEach(function (device) {
				dispatch(REQUEST_API, {
					rule: `api/devices/${device}`,
					method: 'POST',
					data: {tags: payload.tags}
				})
			})
		}
	}
}