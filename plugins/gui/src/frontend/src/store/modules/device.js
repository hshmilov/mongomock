/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'
import merge from 'deepmerge'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_DEVICES_COUNT = 'FETCH_DEVICES_COUNT'
export const UPDATE_DEVICES_COUNT = 'UPDATE_DEVICES_COUNT'
export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'
export const SELECT_DEVICE_PAGE = 'SELECT_DEVICE_PAGE'
export const FETCH_DEVICE_FIELDS = 'FETCH_DEVICE_FIELDS'
export const UPDATE_DEVICE_FIELDS = 'UPDATE_DEVICE_FIELDS'
export const FETCH_TAGS = 'FETCH_TAGS'
export const UPDATE_TAGS = 'UPDATE_TAGS'
export const CREATE_DEVICE_TAGS = 'CREATE_DEVICE_TAGS'
export const ADD_DEVICE_TAGS = 'ADD_DEVICE_TAGS'
export const DELETE_DEVICE_TAGS = 'DELETE_DEVICE_TAGS'
export const REMOVE_DEVICE_TAGS = 'REMOVE_DEVICE_TAGS'


export const mergeDeviceData = (adapters, requiredFields) => {
	return merge.all(adapters.map((adapter) => {
		return requiredFields.reduce((map, field) => {
			if (adapter.data[field]) {
				map[field] = adapter.data[field]
			}
			return map
		}, {})
	}))
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
		deviceFields: {fetching: false, data: {}, error: ''},

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
					if (!device.tags) device.tags = []

					processedData.push({
						id: device['internal_axon_id'],
						adapters: {
							data: merge.all(device.adapters).data,
							plugin_name: device.adapters.map((adapter) => {
								return adapter['plugin_name']
							})
						},
						tags: device.tags.filter((tag) => {
							return tag.type === 'label' && tag.data
						})
					})
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

				state.deviceDetails.data = {
					...payload.data,
					data: merge.all(payload.data.adapters).data,
					tags: payload.data.tags.filter((tag) => {
						return tag.type === 'label' && tag.data
					}),
					dataTags: payload.data.tags.filter((tag) => {
						return tag.type === 'data' && tag.data
					})
				}
			}
		},
		[ UPDATE_DEVICE_FIELDS ] (state, payload) {
			state.deviceFields.fetching = payload.fetching
			state.deviceFields.error = payload.error
			if (!payload.fetching) {
				state.deviceFields.data = payload.data
				state.deviceFields.data.generic.name = 'adapters.data'
				if (state.deviceFields.data.specific) {
					Object.keys(state.deviceFields.data.specific).forEach((specificKey) => {
						state.deviceFields.data.specific[specificKey].name ='adapters.data'
					})
				}
			}
		},
		[ UPDATE_TAGS ] (state, payload) {
			state.tagList.fetching = payload.fetching
			state.tagList.error = payload.error
			if (!payload.fetching) state.tagList.data = payload.data
		},
		[ ADD_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [...state.deviceList.data]
			state.deviceList.data.forEach(function (device) {
				if (!payload.devices.includes(device.id)) return
				if (!device.tags) device.tags = []

				let deviceTags = new Set(device.tags.map((tag) => {
					return tag.name
				}))
				payload.labels.forEach((tag) => {
					if (deviceTags.has(tag)) return
					device.tags.push({ name: tag, type: 'label', data: true })
				})
			})
			payload.labels.forEach((tag) => {
				if (!state.tagList.data || !state.tagList.data.includes(tag)) {
					state.tagList.data.push(tag)
				}
			})
			if (state.deviceDetails.data && state.deviceDetails.data.internal_axon_id
				&& payload.devices.includes(state.deviceDetails.data.internal_axon_id)) {
				state.deviceList.data = { ...state.deviceDetails.data,
					tags: Array.from(new Set([ ...state.deviceDetails.data.tags,
						...payload.labels
					]))
				}
			}
		},
		[ REMOVE_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [...state.deviceList.data]
			state.deviceList.data.forEach((device) => {
				if (!payload.devices.includes(device.id)) return
				if (!device.tags) { return }

				device.tags = device.tags.filter((tag) => {
					return !payload.labels.includes(tag.name)
				})
			})
			state.tagList.data = state.tagList.data.filter((tag) => {
				if (!payload.labels.includes(tag)) return true
				let exists = false
				state.deviceList.data.forEach((device) => {
					if (!device.tags) return
					device.tags.forEach((deviceTag) => {
						if (deviceTag.name === tag) {
							exists = true
						}
					})
				})
				return exists
			})
			if (state.deviceDetails.data && state.deviceDetails.data.internal_axon_id
				&& payload.devices.includes(state.deviceDetails.data.internal_axon_id)
				&& state.deviceDetails.data.tags) {

				state.deviceDetails.data = { ...state.deviceDetails.data,
					tags: state.deviceDetails.data.tags.filter((tag) => {
						return !payload.labels.includes(tag.name)
					})
				}
			}
		},
		[ SELECT_DEVICE_PAGE ] (state, pageNumber) {
			state.deviceSelectedPage = pageNumber
		}
	},
	actions: {
		[ FETCH_DEVICES ] ({dispatch, commit}, payload) {
			/* Fetch list of devices for requested page and filtering */
			if (!payload.skip) {
				payload.skip = 0
				dispatch(FETCH_DEVICES_COUNT, { filter: payload.filter })
			}
			if (!payload.limit) { payload.limit = 0 }
			/* Getting first page - empty table */
			if (payload.skip === 0) { commit(RESTART_DEVICES) }
			let param = `?limit=${payload.limit}&skip=${payload.skip}`
			if (payload.fields && payload.fields.length) {
				param += `&fields=internal_axon_id,tags.type,tags.data,${payload.fields}`
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
		[ FETCH_DEVICE_FIELDS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `/api/devices/fields`,
				type: UPDATE_DEVICE_FIELDS
			})
		},
		[ FETCH_TAGS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `/api/devices/labels`,
				type: UPDATE_TAGS
			})
		},
		[ CREATE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.labels || !payload.labels.length) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: `/api/devices/labels`,
				method: 'POST',
				data: payload
			}).then(() => commit(ADD_DEVICE_TAGS, payload))
		},
		[ DELETE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.labels || !payload.labels.length) {
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