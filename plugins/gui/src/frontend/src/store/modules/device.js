/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'
import { UPDATE_ADAPTERS, adapterStaticData, adapter } from './adapter'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_UNIQUE_FIELDS = 'FETCH_UNIQUE_FIELDS'
export const UPDATE_UNIQUE_FIELDS = 'UPDATE_UNIQUE_FIELDS'
export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'

export const FETCH_TAGS = 'FETCH_TAGS'
export const UPDATE_TAGS = 'UPDATE_TAGS'
export const CREATE_DEVICE_TAGS = 'CREATE_DEVICE_TAGS'
export const ADD_DEVICE_TAGS = 'ADD_DEVICE_TAGS'
export const DELETE_DEVICE_TAGS = 'DELETE_DEVICE_TAGS'
export const REMOVE_DEVICE_TAGS = 'REMOVE_DEVICE_TAGS'
export const SELECT_FIELDS = 'SELECT_FIELDS'

export const decomposeFieldPath = (data, fieldPath) => {
	/*
		Find ultimate value of data, matching given field path, by recursively drilling into the dictionary,
		until path exhausted or reached undefined.
		Arrays along the way will be traversed so that final value is the list of all found values
	 */
	if (!data) { return '' }
	if (typeof(data) === 'string' || (Array.isArray(data) && (!data.length || typeof(data[0]) === 'string'))) {
		return data
	}
	if (Array.isArray(data)) {
		let aggregatedValues = []
		data.forEach((item) => {
			let foundValue = decomposeFieldPath(item, fieldPath)
			if (!foundValue) { return }
			if (Array.isArray(foundValue)) {
				aggregatedValues = aggregatedValues.concat(foundValue)
			} else {
				aggregatedValues.push(foundValue)
			}
		})
		return aggregatedValues
	}
	if (fieldPath.indexOf('.') === -1) { return decomposeFieldPath(data[fieldPath], '') }
	let firstPointIndex = fieldPath.indexOf('.')
	return decomposeFieldPath(data[fieldPath.substring(0, firstPointIndex)], fieldPath.substring(firstPointIndex + 1))
}

export const findValues = (field, data) => {
	let value = []
	field.path.split(',').forEach((currentPath) => {
		value = value.concat(decomposeFieldPath({ ...data }, currentPath))
	})
	if ((!field.type || field.type.indexOf('list') === -1) && Array.isArray(value)) {
		return (value.length > 0) ? value[0] : ''
	}
	return value
}

export const processDevice = (device, fields, filterSelected) => {
	if (!device.adapters || !device.adapters.length) { return }
	let processedDevice = { id: device['internal_axon_id']}
	fields.common.forEach((field) => {
		if (filterSelected && !field.selected) { return }
		let value = findValues(field, device)
		if (value) { processedDevice[field.path] = value }
	})
	device.adapters.forEach((adapter) => {
		if (!fields.unique[adapter.plugin_name]) { return }
		fields.unique[adapter.plugin_name].forEach((field) => {
			if (filterSelected && !field.selected) { return }
			let currentValue = adapter
			let keys = field.path.split('.').splice(1)
			let keysIndex = 0
			while (currentValue && keysIndex < keys.length) {
				currentValue = currentValue[keys[keysIndex]]
				keysIndex++
			}
			processedDevice[field.path] = currentValue
		})
	})
	if (processedDevice['tags.tagvalue']) {
		processedDevice['tags.tagvalue'] = processedDevice['tags.tagvalue'].filter((tag, index, self) => {
			return self.indexOf(tag) === index
		})
	}
	return processedDevice
}

export const device = {
	state: {
		/* Devices according to some query performed by user, updating by request */
		deviceList: {fetching: false, data: [], error: ''},

		/* Currently selected devices, without censoring */
		deviceDetails: {fetching: false, data: {}, error: ''},

		/* Configurations specific for devices */
		fields: {
			common: [
				{path: 'internal_axon_id', name: '', hidden: true, selected: true},
				{
					path: 'adapters.plugin_name', name: 'Adapters', selected: true, type: 'image-list', control: 'multiple-select',
					options: []
				},
				{path: 'adapters.data.pretty_id', name: 'Axonius Name', selected: true, control: 'text'},
				{path: 'adapters.data.name', name: 'Host Name', selected: true, control: 'text'},
				{
					path: 'adapters.data.network_interfaces.public_ip,adapters.data.network_interfaces.private_ip',
					name: 'IP Addresses',
					selected: true,
					type: 'list'
				},
				{path: 'adapters.data.OS.type', name: 'Operating System', selected: true, control: 'text'},
				{path: 'tags.tagvalue', name: 'Tags', selected: true, type: 'tag-list', control: 'multiple-select', options: []}
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
			state.deviceList.error = payload.error
			if (payload.data) {
				let processedData = []
				payload.data.forEach((device) => {
					processedData.push(processDevice(device, state.fields, true))
				})
				state.deviceList.data = [...state.deviceList.data, ...processedData]
			}
		},
		[ UPDATE_DEVICE ] (state, payload) {
			state.deviceDetails.fetching = payload.fetching
			state.deviceDetails.error = payload.error
			if (payload.data) {
				state.deviceDetails.data = processDevice(payload.data, state.fields)
			}
		},
		[ UPDATE_UNIQUE_FIELDS ] (state, payload) {
			if (payload.data) {
				state.fields.unique = {}
				Object.keys(payload.data).forEach(function (pluginName) {
					state.fields.unique[pluginName] = []
					payload.data[pluginName].forEach((fieldPath) => {
						let fieldName = fieldPath.split('.').splice(3).join('.')
						state.fields.unique[pluginName].push({
							path: fieldPath,
							name: `${adapterStaticData[pluginName].name}.${fieldName}`,
							control: 'text'
						})
					})
				})
			}
		},
		[ UPDATE_TAGS ] (state, payload) {
			state.tagList.fetching = payload.fetching
			state.tagList.error = payload.error
			if (payload.data) {
				state.tagList.data = payload.data.map(function (tag) {
					return {name: tag, path: tag}
				})
				state.fields.common.forEach(function (field) {
					if (field.path === 'tags.tagvalue') {
						field.options = state.tagList.data
					}
				})
			}
		},
		[ ADD_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [ ...state.deviceList.data ]
			state.deviceList.data.forEach(function (device) {
				if (payload.devices.indexOf(device['id']) > -1) {
					if (!device['tags.tagvalue']) { device['tags.tagvalue'] = [] }
					payload.tags.forEach((tag) => {
						if (device['tags.tagvalue'].indexOf(tag) !== -1) { return }
						device['tags.tagvalue'].push(tag)
					})
				}
			})
			let tags = state.tagList.data.map((tag) => {
				return tag.path
			})
			payload.tags.forEach(function (tag) {
				if (tags.indexOf(tag) === -1) {
					state.tagList.data.push({name: tag, path: tag})
				}
			})
		},
		[ REMOVE_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [ ...state.deviceList.data ]
			state.deviceList.data.forEach((device) => {
				if (payload.devices.indexOf(device['id']) > -1) {
					if (!device['tags.tagvalue']) { return }
					device['tags.tagvalue'] = device['tags.tagvalue'].filter((tag) => {
						return payload.tags.indexOf(tag) === -1
					})
				}
			})
		},
		[ SELECT_FIELDS ] (state, payload) {
			state.fields.common.forEach((field) => {
				field.selected = payload.indexOf(field.path) > -1
			})
			Object.values(state.fields.unique).forEach((pluginFields) => {
				pluginFields.forEach((field) => {
					field.selected = payload.indexOf(field.path) > -1
				})
			})
		},
		[ UPDATE_ADAPTERS ] (state, payload) {
			if (!payload.data) { return }
			state.fields.common.forEach((field) => {
				if (field.path !== 'adapters.plugin_name') { return }
				field.options = []
				let used = new Set()
				payload.data.forEach((adapter) => {
					if (used.has(adapter.plugin_name)) { return }
					field.options.push({name: adapterStaticData[adapter.plugin_name].name, path: adapter.plugin_name})
					used.add(adapter.plugin_name)
				})
			})
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
				commit(SELECT_FIELDS, payload.fields)
				param += `&fields=${payload.fields}`
			}
			if (payload.filter && Object.keys(payload.filter).length) {
				param += `&filter=${JSON.stringify(payload.filter)}`
			}
			dispatch(REQUEST_API, {
				rule: `/api/devices${param}`,
				type: UPDATE_DEVICES
			})
		},
		[ FETCH_DEVICE ] ({dispatch}, deviceId) {
			if (!deviceId) { return }
			dispatch(REQUEST_API, {
				rule: `/api/devices/${deviceId}`,
				type: UPDATE_DEVICE
			})
		},
		[ FETCH_UNIQUE_FIELDS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `/api/devices/fields`,
				type: UPDATE_UNIQUE_FIELDS
			})
		},
		[ FETCH_TAGS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `/api/devices/tags`,
				type: UPDATE_TAGS
			})
		},
		[ CREATE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.tags || !payload.tags.length) {
				return
			}
			commit(ADD_DEVICE_TAGS, payload)
			payload.devices.forEach(function (device) {
				dispatch(REQUEST_API, {
					rule: `/api/devices/${device}`,
					method: 'POST',
					data: {tags: payload.tags}
				})
			})
		},
		[ DELETE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.tags || !payload.tags.length) {
				return
			}
			commit(REMOVE_DEVICE_TAGS, payload)
			payload.devices.forEach(function (device) {
				dispatch(REQUEST_API, {
					rule: `/api/devices/${device}/tags`,
					method: 'DELETE',
					data: {tags: payload.tags}
				})
			})
		}
	}
}