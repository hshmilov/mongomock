/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'
import { UPDATE_ADAPTERS, adapterStaticData } from './adapter'
import merge from 'deepmerge'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_DEVICES_COUNT = 'FETCH_DEVICES_COUNT'
export const UPDATE_DEVICES_COUNT = 'UPDATE_DEVICES_COUNT'
export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'
export const SELECT_DEVICE_PAGE = 'SELECT_DEVICE_PAGE'

export const FETCH_TAGS = 'FETCH_TAGS'
export const UPDATE_TAGS = 'UPDATE_TAGS'
export const CREATE_DEVICE_TAGS = 'CREATE_DEVICE_TAGS'
export const ADD_DEVICE_TAGS = 'ADD_DEVICE_TAGS'
export const DELETE_DEVICE_TAGS = 'DELETE_DEVICE_TAGS'
export const REMOVE_DEVICE_TAGS = 'REMOVE_DEVICE_TAGS'
export const SELECT_FIELDS = 'SELECT_FIELDS'


export const decomposeFieldPath = (data, fieldPath) => {
	/*
		Find ultimate value of controls, matching given field path, by recursively drilling into the dictionary,
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
		value = value.concat(decomposeFieldPath({...data}, currentPath))
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
	let processedDevice = {id: device['internal_axon_id']}
	fields.common.forEach((field) => {
		if (!field.selected) { return }
		let value = findValues(field, device)
		if (value) { processedDevice[field.path] = value }
	})
	if (device['tags']) {
		processedDevice['tags.name'] = device['tags'].filter((tag) => {
			return tag.type === 'label' && tag.data
		}).map((tag) => {
			return tag.name
		})
		processedDevice['tags.name'] = processedDevice['tags.name'].filter((tag, index, self) => {
			return self.indexOf(tag) === index
		})
	}
	return processedDevice
}

export const device = {
	state: {
		/* Devices according to current filter performed by user, updating by request */
		deviceList: {fetching: false, data: [], error: ''},

		deviceSelectedPage: 0,

		/* Number of devices according to current filter performed by user */
		deviceCount: {fetching: false, data: 0, error: ''},

		/* Currently selected devices, without censoring */
		deviceDetails: {fetching: false, data: {}, error: ''},

		/* All fields parsed in the system - at least one adapter parses the field */
		deviceFields: {
			fetching: false, data: {
				'name': 'data',
				'items': [
					{
						'title': 'Axonius Name',
						'name': 'pretty_id',
						'type': 'string'
					},
					{
						'title': 'ID',
						'name': 'id',
						'type': 'string'
					},
					{
						'title': 'Asset Name',
						'name': 'name',
						'type': 'string'
					},
					{
						'title': 'Host Name',
						'name': 'hostname',
						'type': 'string'
					},
					{
						'name': 'os',
						'items': [
							{
								'title': 'OS Type',
								'enum': [
									'Windows',
									'Linux',
									'OS X',
									'iOS',
									'Android'
								],
								'name': 'type',
								'type': 'string'
							},
							{
								'title': 'OS Distribution',
								'name': 'distribution',
								'type': 'string'
							},
							{
								'title': 'OS Bitness',
								'enum': [
									32,
									64
								],
								'name': 'bitness',
								'type': 'integer'
							},
							{
								'title': 'OS Major',
								'name': 'major',
								'type': 'string'
							},
							{
								'title': 'OS Minor',
								'name': 'minor',
								'type': 'string'
							}
						],
						'type': 'array'
					},
					{
						'items': {
							'items': [
								{
									'title': 'MAC',
									'name': 'mac',
									'type': 'string'
								},
								{
									'title': 'IP',
									'items': {
										'type': 'string',
										'format': 'ip'
									},
									'name': 'ips',
									'type': 'array'
								}
							],
							'type': 'array'
						},
						'name': 'network_interfaces',
						'title': 'Network Interface',
						'type': 'array'
					},
					{
						'title': 'Last Seen',
						'name': 'last_seen',
						'type': 'string',
						'format': 'date-time'
					},
					{
						'title': 'VM Tools Status',
						'name': 'vm_tools_status',
						'type': 'string'
					},
					{
						'title': 'Resolve Status',
						'name': 'dns_resolve_status',
						'type': 'string'
					},
					{
						'title': 'Power State',
						'name': 'power_state',
						'type': 'string'
					},
					{
						'title': 'Physical Path',
						'name': 'vm_physical_path',
						'type': 'bool'
					}
				],
				'type': 'array',
				'required': ['pretty_id', 'name', 'hostname', 'os', 'network_interfaces']
			}, error: ''
		},

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
					options: []
				},
				{path: 'adapters.data.pretty_id', name: 'Axonius Name', selected: false, control: 'text'},
				{path: 'adapters.data.hostname', name: 'Host Name', selected: true, control: 'text'},
				{path: 'adapters.data.name', name: 'Asset Name', selected: true, control: 'text'},
				{
					path: 'adapters.data.network_interfaces.ips',
					name: 'IPs',
					selected: true,
					type: 'list',
					control: 'text'
				},
				{
					path: 'adapters.data.network_interfaces.mac',
					name: 'MACs',
					selected: false,
					type: 'list',
					control: 'text'
				},
				{path: 'adapters.data.os.type', name: 'OS', selected: true, control: 'text'},
				{path: 'adapters.data.os.distribution', name: 'OS Version', selected: false, control: 'text'},
				{path: 'adapters.data.os.bitness', name: 'OS Bitness', selected: false, control: 'text'},
				{
					path: 'tags.name',
					name: 'Tags',
					selected: true,
					type: 'tag-list',
					control: 'multiple-select',
					options: []
				},
				{path: 'tags.data', selected: true, hidden: true},
				{path: 'last_used_user', selected: false, name: 'Last User Logged'}
			]
		},

		tagList: {fetching: false, data: [], error: ''},
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
			if (payload.data !== undefined) {
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
						if (adapter.data[field]) {
							requiredData[field] = adapter.data[field]
						}
					})
					return requiredData
				})
				state.deviceDetails.data = {
					...payload.data,
					data: merge.all(adapterDatas),
					tags: payload.data.tags.filter((tag) => {
						return tag.tagtype === 'label' && tag.data
					}),
					dataTags: payload.data.tags.filter((tag) => {
						return tag.tagtype === 'data' && tag.data
					})
				}
			}
		},
		[ UPDATE_TAGS ] (state, payload) {
			state.tagList.fetching = payload.fetching
			state.tagList.error = payload.error
			if (payload.data) {
				state.tagList.data = payload.data.map((tag) => {
					return {name: tag, path: tag}
				})
				state.fields.common.forEach((field) => {
					if (field.path === 'tags.name') {
						field.options = state.tagList.data
					}
				})
			}
		},
		[ ADD_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [...state.deviceList.data]
			state.deviceList.data.forEach(function (device) {
				if (payload.devices.indexOf(device['id']) > -1) {
					if (!device['tags.name']) { device['tags.name'] = [] }
					payload.tags.forEach((tag) => {
						if (device['tags.name'].indexOf(tag) !== -1) { return }
						device['tags.name'].push(tag)
					})
				}
			})
			let tags = state.tagList.data.map((tag) => {
				return tag.path
			})
			payload.tags.forEach((tag) => {
				if (tags.indexOf(tag) === -1) {
					state.tagList.data.push({name: tag, path: tag})
				}
			})
			state.fields.common.forEach((field) => {
				if (field.path === 'tags.name') {
					field.options = state.tagList.data
				}
			})
			if (state.deviceDetails.data && state.deviceDetails.data.internal_axon_id
				&& payload.devices.includes(state.deviceDetails.data.internal_axon_id)) {
				state.deviceList.data = { ...state.deviceDetails.data,
					tags: Array.from(new Set([ ...state.deviceDetails.data.tags,
						...payload.tags
					]))
				}
			}
		},
		[ REMOVE_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [...state.deviceList.data]
			state.deviceList.data.forEach((device) => {
				if (payload.devices.indexOf(device['id']) > -1) {
					if (!device['tags.name']) { return }
					device['tags.name'] = device['tags.name'].filter((tag) => {
						return payload.tags.indexOf(tag) === -1
					})
				}
			})
			state.tagList.data = state.tagList.data.filter((tag) => {
				if (!payload.tags.includes(tag.path)) { return true }
				let exists = false
				state.deviceList.data.forEach((device) => {
					if (!device['tags.name']) { return }
					device['tags.name'].forEach((deviceTag) => {
						if (deviceTag === tag.path) {
							exists = true
						}
					})
				})
				return exists

			})
			state.fields.common.forEach((field) => {
				if (field.path === 'tags.name') {
					field.options = state.tagList.data
				}
			})
			if (state.deviceDetails.data && state.deviceDetails.data.internal_axon_id
				&& payload.devices.includes(state.deviceDetails.data.internal_axon_id)
				&& state.deviceDetails.data.tags) {

				state.deviceDetails.data = { ...state.deviceDetails.data,
					tags: state.deviceDetails.data.tags.filter((tag) => {
						return !payload.tags.includes(tag.name)
					})
				}
			}
		},
		[ SELECT_FIELDS ] (state, payload) {
			state.fields.common.forEach((field) => {
				field.selected = payload.indexOf(field.path) > -1
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
		},
		[ SELECT_DEVICE_PAGE ] (state, pageNumber) {
			state.deviceSelectedPage = pageNumber
		}
	},
	actions: {
		[ FETCH_DEVICES ] ({dispatch, commit}, payload) {
			/* Fetch list of devices for requested page and filtering */
			if (!payload.skip) { payload.skip = 0 }
			if (!payload.limit) { payload.limit = 0 }
			/* Getting first page - empty table */
			if (payload.skip === 0) { commit(RESTART_DEVICES) }
			let param = `?limit=${payload.limit}&skip=${payload.skip}`
			if (payload.fields && payload.fields.length) {
				commit(SELECT_FIELDS, payload.fields)
				param += `&fields=${payload.fields}`
			}
			if (payload.filter && payload.filter.length) {
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
		[ FETCH_TAGS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `/api/devices/labels`,
				type: UPDATE_TAGS
			})
		},
		[ CREATE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.tags || !payload.tags.length) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: `/api/devices/labels`,
				method: 'POST',
				data: payload
			}).then(() => commit(ADD_DEVICE_TAGS, payload))
		},
		[ DELETE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.tags || !payload.tags.length) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: `/api/devices/labels`,
				method: 'DELETE',
				data: payload
			}).then(() => commit(REMOVE_DEVICE_TAGS, payload))
		}
	}
}