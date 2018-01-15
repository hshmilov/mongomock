/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'
import { UPDATE_ADAPTERS, adapterStaticData } from './adapter'
import merge from 'deepmerge'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_DEVICES_COUNT = 'FETCH_DEVICES_COUNT'
export const UPDATE_DEVICES_COUNT = 'UPDATE_DEVICES_COUNT'
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
	} else if (Array.isArray(value)) {
		return Array.from(new Set(value))
	}
	return value
}

export const processDevice = (device, fields) => {
	if (!device.adapters || !device.adapters.length) { return }
	let processedDevice = { id: device['internal_axon_id']}
	fields.common.forEach((field) => {
		if (!field.selected) { return }
		let value = findValues(field, device)
		if (value) { processedDevice[field.path] = value }
	})
	device.adapters.forEach((adapter) => {
		if (!fields.unique[adapter.plugin_name]) { return }
		fields.unique[adapter.plugin_name].forEach((field) => {
			if (!field.selected) { return }
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
	if (device['tags']) {
	   device['tags'].filter((tag) => {
		  return tag.tagname === 'FIELD'
	   }).forEach((tag) => {
		  processedDevice[tag.tagvalue.fieldname] = tag.tagvalue.fieldvalue
	   })
	   processedDevice['tags.tagname'] = device['tags'].filter((tag) => {
		  return tag.tagname !== 'FIELD' && tag.tagvalue !== undefined && tag.tagvalue !== ''
	   }).map((tag) => {
		  return tag.tagname
	   })
	   processedDevice['tags.tagname'] = processedDevice['tags.tagname'].filter((tag, index, self) => {
		  return self.indexOf(tag) === index
	   })
	}
	return processedDevice
}

export const device = {
	state: {
		/* Devices according to current filter performed by user, updating by request */
		deviceList: {fetching: false, data: [], error: ''},

		/* Number of devices according to current filter performed by user */
		deviceCount: {fetching: false, data: 0, error: ''},

		/* Currently selected devices, without censoring */
		deviceDetails: {fetching: false, data: {}, error: ''},

		/* All fields parsed in the system - at least one adapter parses the field */
		deviceFields: {fetching: false, data: {
			"items": [
				{
					"title": "Axonius Name",
					"name": "pretty_id",
					"type": "string"
				},
				{
					"title": "Device Name",
					"name": "name",
					"type": "string"
				},
				{
					"title": "Host Name",
					"format": "hostname",
					"name": "hostname",
					"type": "string"
				},
				{
					"name": "OS",
					"items": [
						{
							"title": "OS",
							"enum": [
								"Windows",
								"Linux",
								"OS X",
								"iOS",
								"Android"
							],
							"name": "type",
							"type": "string"
						},
						{
							"title": "OS Distribution",
							"name": "distribution",
							"type": "string"
						},
						{
							"title": "OS Bitness",
							"enum": [
								32,
								64
							],
							"name": "bitness",
							"type": "number"
						}
					],
					"type": "array"
				},
				{
					"title": "Network Interfaces",
					"items": {
						"items": [
							{
								"title": "MAC",
								"name": "MAC",
								"type": "string"
							},
							{
								"title": "IPs",
								"items": {
									"type": "string"
								},
								"name": "IP",
								"type": "array"
							},
							{
								"title": "Interface Type",
								"name": "nic_type",
								"type": "string"
							}
						],
						"type": "array"
					},
					"name": "network_interfaces",
					"type": "array"
				},
				{
					"title": "VM Tools Status",
					"name": "vmToolsStatus",
					"type": "string"
				}
			],
			"type": "array",
			"required": ["pretty_id", "name", "hostname", "OS", "network_interfaces"]
		}, error: ''},

		/* Configurations specific for devices */
		fields: {
			common: [
				{path: 'internal_axon_id', name: '', hidden: true, selected: true},
				{
					path: 'adapters.plugin_name', name: 'Adapters', selected: true, type: 'image-list', control: 'multiple-select',
					options: []
				},
				{path: 'adapters.data.pretty_id', name: 'Axonius Name', selected: false, control: 'text'},
				{path: 'adapters.data.hostname', name: 'Host Name', selected: true, control: 'text'},
				{path: 'adapters.data.name', name: 'Asset Name', selected: true, control: 'text'},
				{
					path: 'adapters.data.network_interfaces.IP',
					name: 'IPs',
					selected: true,
					type: 'list',
					control: 'text'
				},
				{
					path: 'adapters.data.network_interfaces.MAC',
					name: 'MACs',
					selected: false,
					type: 'list',
					control: 'text'
				},
				{path: 'adapters.data.OS.type', name: 'OS', selected: true, control: 'text'},
				{path: 'adapters.data.OS.distribution', name: 'OS Version', selected: false, control: 'text'},
				{path: 'adapters.data.OS.bitness', name: 'OS Bitness', selected: false, control: 'text'},
				{path: 'tags.tagname', name: 'Tags', selected: true, type: 'tag-list', control: 'multiple-select', options: []},
				{path: 'tags.tagvalue', selected: true, hidden: true},
				{path: 'last_used_user', selected: false, name: 'Last User Logged'}
			],
			unique: {}
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
					processedData.push(processDevice(device, state.fields))
				})
				state.deviceList.data = [...state.deviceList.data, ...processedData]
			}
		},
		[ UPDATE_DEVICES_COUNT ] (state, payload) {
			state.deviceCount.fetching = payload.fetching
			state.deviceCount.error = payload.error
			if (payload.data) {
				state.deviceCount.data = payload.data
			}
		},
		[ UPDATE_DEVICE ] (state, payload) {
			state.deviceDetails.fetching = payload.fetching
			state.deviceDetails.error = payload.error
			if (payload.data) {
				let adapterDatas = payload.data.adapters.map((adapter) => {
					let requiredData = {}
					state.deviceFields.data.required.forEach((field) => {
						requiredData[field] = adapter.data[field]
					})
					return requiredData
				})
				state.deviceDetails.data = {
					...payload.data,
					data: merge.all(adapterDatas),
					tags: payload.data.tags.filter((tag) => {
						return tag.tagname !== 'FIELD' && tag.tagvalue !== undefined && tag.tagvalue !== ''
					})
				}
			}
		},
		[ UPDATE_UNIQUE_FIELDS ] (state, payload) {
			if (payload.data) {
				state.fields.unique = {}
				Object.keys(payload.data).forEach(function (pluginName) {
					state.fields.unique[pluginName] = []
					payload.data[pluginName].forEach((field) => {
						let fieldName = field.path.split('.').splice(3).join('.')
						state.fields.unique[pluginName].push({
							path: field.path,
							name: `${adapterStaticData[pluginName].name}.${fieldName}`,
							control: field.control
						})
					})
				})
			}
		},
		[ UPDATE_TAGS ] (state, payload) {
            state.tagList.fetching = payload.fetching
            state.tagList.error = payload.error
            if (payload.data) {
                state.tagList.data = payload.data.filter((tag) => {
                    return tag !== 'FIELD' && tag !== ''
                }).map(function (tag) {
                    return {name: tag, path: tag}
                })
                state.fields.common.forEach(function (field) {
                    if (field.path === 'tags.tagname') {
                        field.options = state.tagList.data
                    }
                })
            }
        },
		[ ADD_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [ ...state.deviceList.data ]
			state.deviceList.data.forEach(function (device) {
				if (payload.devices.indexOf(device['id']) > -1) {
					if (!device['tags.tagname']) { device['tags.tagname'] = [] }
					payload.tags.forEach((tag) => {
						if (device['tags.tagname'].indexOf(tag) !== -1) { return }
						device['tags.tagname'].push(tag)
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
					if (!device['tags.tagname']) { return }
					device['tags.tagname'] = device['tags.tagname'].filter((tag) => {
						return payload.tags.indexOf(tag) === -1
					})
				}
			})
			state.deviceDetails.data = { ...state.deviceDetails.data,
				tags: state.deviceDetails.data.tags.filter((tag) => {
					return !payload.tags.includes(tag.tagname)
				})
			}
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
					let name = adapter.plugin_name
					if (adapterStaticData[adapter.plugin_name]) {
						name = adapterStaticData[adapter.plugin_name].name
					}
					field.options.push({name: name, path: adapter.plugin_name})
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
				param += `&filter=${payload.filter}`
			}
			dispatch(REQUEST_API, {
				rule: `/api/devices${param}`,
				type: UPDATE_DEVICES
			})
		},
		[ FETCH_DEVICES_COUNT ] ({dispatch}, payload) {
			let param = ''
			if (payload && payload.filter && Object.keys(payload.filter).length) {
				param = `?filter=${payload.filter}`
			}
			dispatch(REQUEST_API, {
				rule: `/api/devices/count${param}`,
				type: UPDATE_DEVICES_COUNT
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