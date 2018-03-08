/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'
import merge from 'deepmerge'

export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'
export const FETCH_DEVICE_FIELDS = 'FETCH_DEVICE_FIELDS'
export const UPDATE_DEVICE_FIELDS = 'UPDATE_DEVICE_FIELDS'
export const FETCH_LABELS = 'FETCH_LABELS'
export const UPDATE_LABELS = 'UPDATE_LABELS'
export const CREATE_DEVICE_LABELS = 'CREATE_DEVICE_LABELS'
export const ADD_DEVICE_LABELS = 'ADD_DEVICE_LABELS'
export const DELETE_DEVICE_LABELS = 'DELETE_DEVICE_LABELS'
export const REMOVE_DEVICE_LABELS = 'REMOVE_DEVICE_LABELS'


export const device = {
	state: {
		dataTable: {
			content: { data: [], fetching: false, error: ''},
			count: { data: 0, fetching: false, error: ''},
			view: {
				page: 0, pageSize: 20, fields: [
					'adapters', 'specific_data.data.hostname', 'specific_data.data.name',
					'specific_data.data.network_interfaces.ips', 'specific_data.data.os.type', 'labels'
				], coloumnSizes: [], filter: '', sort: {field: '', desc: true}
			}
		},

		/* Currently selected devices, without censoring */
		deviceDetails: {fetching: false, data: {}, error: ''},

		/* All fields parsed in the system - at least one adapter parses the field */
		deviceFields: {fetching: false, data: {}, error: ''},

		labelList: {fetching: false, data: [], error: ''},
	},
	getters: {},
	mutations: {
		[ UPDATE_DEVICE ] (state, payload) {
			state.deviceDetails.fetching = payload.fetching
			state.deviceDetails.error = payload.error
			if (payload.data) {
				state.deviceDetails.data = {
					...payload.data,
					specific_data: payload.data.specific_data,
					generic_data: [ merge.all(payload.data.specific_data).data, ...payload.data.generic_data ],
					labels: payload.data.labels
				}
			}
		},
		[ UPDATE_DEVICE_FIELDS ] (state, payload) {
			state.deviceFields.fetching = payload.fetching
			state.deviceFields.error = payload.error
			if (!payload.fetching) {
				state.deviceFields.data = payload.data
				state.deviceFields.data.generic.name = 'specific_data.data'
				if (state.deviceFields.data.specific) {
					Object.keys(state.deviceFields.data.specific).forEach((specificKey) => {
						state.deviceFields.data.specific[specificKey].name = `adapters_data.${specificKey}`
					})
				}
			}
		},
		[ UPDATE_LABELS ] (state, payload) {
			state.labelList.fetching = payload.fetching
			state.labelList.error = payload.error
			if (!payload.fetching) state.labelList.data = payload.data
		},
		[ ADD_DEVICE_LABELS ] (state, payload) {
			state.dataTable.content.data = [...state.dataTable.content.data]
			state.dataTable.content.data.forEach(function (device) {
				if (!payload.devices.includes(device.id)) return
				if (!device.labels) device.labels = []

				device.labels = Array.from(new Set([ ...device.labels, ...payload.labels ]))
			})
			state.labelList.data = Array.from(new Set([ ...state.labelList.data, ...payload.labels ]))

			if (state.deviceDetails.data && state.deviceDetails.data.internal_axon_id
				&& payload.devices.includes(state.deviceDetails.data.internal_axon_id)) {
				state.deviceDetails.data = { ...state.deviceDetails.data,
					labels: Array.from(new Set([ ...state.deviceDetails.data.labels,
						...payload.labels
					]))
				}
			}
		},
		[ REMOVE_DEVICE_LABELS ] (state, payload) {
			state.dataTable.content.data = [...state.dataTable.content.data]
			state.dataTable.content.data.forEach((device) => {
				if (!payload.devices.includes(device.id)) return
				if (!device.labels) { return }

				device.labels = device.labels.filter((label) => {
					return !payload.labels.includes(label)
				})
			})
			state.labelList.data = state.labelList.data.filter((label) => {
				if (!payload.labels.includes(label)) return true
				let exists = false
				state.dataTable.content.data.forEach((device) => {
					if (!device.labels) return
					exists = exists && device.labels.includes(label)
				})
				return exists
			})
			if (state.deviceDetails.data && state.deviceDetails.data.internal_axon_id
				&& payload.devices.includes(state.deviceDetails.data.internal_axon_id)
				&& state.deviceDetails.data.labels) {

				state.deviceDetails.data = { ...state.deviceDetails.data,
					labels: state.deviceDetails.data.labels.filter((label) => {
						return !payload.labels.includes(label)
					})
				}
			}
		}
	},
	actions: {
		[ FETCH_DEVICE ] ({dispatch}, deviceId) {
			if (!deviceId) { return }
			dispatch(REQUEST_API, {
				rule: `device/${deviceId}`,
				type: UPDATE_DEVICE
			})
		},
		[ FETCH_DEVICE_FIELDS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `device/fields`,
				type: UPDATE_DEVICE_FIELDS
			})
		},
		[ FETCH_LABELS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `device/labels`,
				type: UPDATE_LABELS
			})
		},
		[ CREATE_DEVICE_LABELS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.labels || !payload.labels.length) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: `device/labels`,
				method: 'POST',
				data: payload
			}).then(() => commit(ADD_DEVICE_LABELS, payload))
		},
		[ DELETE_DEVICE_LABELS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.labels || !payload.labels.length) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: `device/labels`,
				method: 'DELETE',
				data: payload
			}).then(() => commit(REMOVE_DEVICE_LABELS, payload))
		}
	}
}