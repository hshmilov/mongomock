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
export const SELECT_FIELDS = 'SELECT_FIELDS'

export const decomposeFieldPath = (data, fieldPath) => {
	/*
		Find ultimate value of data, matching given field path, by recursively drilling into the dictionary,
		until path exhausted or reached undefined.
		Arrays along the way will be traversed so that final value is the list of all found values
	 */
	if (!data || typeof(data) === 'string' || (Array.isArray(data) && (!data.length || typeof(data[0]) === 'string'))) {
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
	if (fieldPath.indexOf('.') === -1) { return data[fieldPath] }
	let firstPointIndex = fieldPath.indexOf('.')
	return decomposeFieldPath(data[fieldPath.substring(0, firstPointIndex)], fieldPath.substring(firstPointIndex + 1))
}

export const findValue = (field, data) => {
	let value = []
	field.path.split(',').forEach((currentPath) => {
		value = value.concat(decomposeFieldPath({ ...data }, currentPath))
	})
	if ((!field.type || field.type.indexOf('list') === -1) && Array.isArray(value)) {
		return (value.length > 0) ? value[0] : ''
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
				{path: 'internal_axon_id', name: '', hidden: true, selected: true},
				{
					path: 'adapters.plugin_name',
					name: 'Adapters',
					selected: true,
					type: 'image-list',
					control: 'multiple-select',
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
				{
					path: 'adapters.data.network_interfaces.public_ip,adapters.data.network_interfaces.private_ip',
					name: 'IP Addresses',
					selected: true,
					type: 'list'
				},
				{path: 'adapters.data.OS.type', name: 'Operating System', selected: true, control: 'text'},
				{path: 'tags.tagname', name: 'Tags', selected: true, type: 'tag-list', control: 'multiple-select', options: []}
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
					let processedDevice = {}
					state.fields.common.forEach((field) => {
						if (!field.selected) { return }
						let value = findValue(field, device)
						if (value) { processedDevice[field.path] = value }
					})
					state.fields.unique.forEach((field) => {
						if (!field.selected) { return }
						let fieldParts = field.path.match(/adapters\.([\w_]*)\.(.*)/)
						let currentValue = device.adapters.filter((adapter) => {
							return adapter.plugin_name === fieldParts[1]
						})[0]
						let keys = fieldParts[2].split('.')
						let keysIndex = 0
						while (currentValue && keysIndex < keys.length) {
							currentValue = currentValue[keys[keysIndex]]
						}
						processedData[field.path] = currentValue
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
					let fieldName = fieldParts.splice(4).join('.')
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
		},
		[ SELECT_FIELDS ] (state, payload) {
			state.fields.common.forEach((field) => {
				field.selected = payload.indexOf(field.path) > -1
			})
			state.fields.unique.forEach((field) => {
				field.selected = payload.indexOf(field.path) > -1
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