import { REQUEST_API } from '../actions'

export const FETCH_LIFECYCLE = 'FETCH_LIFECYCLE'
export const UPDATE_LIFECYCLE = 'UPDATE_LIFECYCLE'

export const FETCH_ADAPTER_DEVICES = 'FETCH_ADAPTER_DEVICES'
export const UPDATE_ADAPTER_DEVICES = 'UPDATE_ADAPTER_DEVICES'

export const dashboard = {
	state: {
		lifecycle: { data: {}, fetching: false, error: '' },
		adapterDevices: { data: {}, fetching: false, error: '' }
	},
	mutations: {
		[ UPDATE_LIFECYCLE ] (state, payload) {
			state.lifecycle.fetching = payload.fetching
			state.lifecycle.error = payload.error
			if (payload.data && payload.data.sub_phases) {
				state.lifecycle.data = {
					subPhases: payload.data.sub_phases,
					nextRunTime: payload.data.next_run_time
				}
			}
		},
		[ UPDATE_ADAPTER_DEVICES] (state, payload) {
			state.adapterDevices.fetching = payload.fetching
			state.adapterDevices.error = payload.error
			if (payload.data && Object.keys(payload.data).length) {
				state.adapterDevices.data = { ...payload.data }
			}
		}
	},
	actions: {
		[ FETCH_LIFECYCLE ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: 'api/dashboard/lifecycle',
				type: UPDATE_LIFECYCLE
			})
		},
		[ FETCH_ADAPTER_DEVICES ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: 'api/dashboard/adapter_devices',
				type: UPDATE_ADAPTER_DEVICES
			})
		}
	}
}