/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const TOGGLE_DEVICE = 'TOGGLE_DEVICE'
export const TOGGLE_DEVICE_ALL = 'TOGGLE_DEVICE_ALL'
export const TOGGLE_DEVICE_FIELD = 'TOGGLE_DEVICE_FIELD'
export const TOGGLE_DEVICE_TAG = 'TOGGLE_DEVICE_TAG'
export const SAVE_DEVICE_TAGS = 'SAVE_DEVICE_TAGS'
export const GET_DEVICE = 'GET_DEVICE'
export const SET_DEVICE = 'SET_DEVICE'

export const device = {
    state: {
        /* Devices according to some query performed by user, updating by request */
        retrievedDevices: {fetching: false, data: [], error: ''},

        /* Info of one device that was requested */
        expandedDevice: {fetching: false, data: {}, error: ''},

        /* Configurations specific for devices */
        fields: [
            {
                path: 'adapters', name: 'Adapters', default: true, selected: true, type: 'image-list', querySchema: {
                type: 'select',
                options: [
                    {text: 'Active Dirsectory', value: 'ad_adapter'},
                    {text: 'ESX', value: 'esx_adapter'},
                    {text: 'Puppet', value: 'pupper_adapter'},
                    {text: 'LDAP', value: 'ldap_adapter'}
                ]
            }
            },
            {
                path: 'data.name', name: 'Device Name', selected: true, querySchema: {
                type: 'text'
            }
            },
            {
                path: 'data.hostname', name: 'Hostname', selected: true, querySchema: {
                type: 'text'
            }
            },
            {path: 'data.network_interfaces.MAC', name: 'MAC Address', selected: false, type: 'list' },
            {path: 'data.network_interfaces.public_ip', name: 'IP Address', selected: false},
            {
                path: 'data.OS.type', name: 'OS Type', selected: true, querySchema: {
                type: 'select'
            }
            },
            {
                path: 'OU', name: 'Operation Unit', selected: false, querySchema: {
                type: 'text'
            }
            },
            {
                path: 'tags', name: 'Tags', default: true, selected: true, type: 'list', querySchema: {
                type: 'text'
            }
            },
            {path: 'data.OS.distribution', name: 'OS Distribution', selected: false}
        ],
        tags: [
            { path: 'software_updates', name: 'Software Updates', selected: false },
            { path: 'devices_of_type', name: 'Devices of Type', selected: false },
            { path: 'hr_ios', name: 'HR iOS Devices', selected: false },
            { path: 'old_version', name: 'Old Version', selected: false }
        ]
    },
    getters: {
        selectedFields (state) {
            return state.fields.filter(function (field) {
                return field.selected
            })
        },
        selectedDevices (state) {
            return state.retrievedDevices.data.filter(function (device) {
                return device.selected
            }).map(function (device) {
                return device['_id']
            })
        },
        deviceNames (state) {
            return state.retrievedDevices.data.map(function (device) {
                return device['name']
            })
        },
        queryFields (state) {
            return state.fields.filter(function (field) {
                return field.querySchema !== undefined
            }).map(function (field) {
                return {
                    path: field.path, name: field.name,
                    ...field.querySchema
                }
            })
        },
        selectedTags (state) {
            return state.tags.filter(function(tag) {
                return tag.selected
            }).map(function(tag) {
                return tag.path
            })
        }
    },
    mutations: {
        [ RESTART_DEVICES ] (state) {
            state.retrievedDevices.data = []
        },
        [ UPDATE_DEVICES ] (state, payload) {
            /* Freshly fetched devices are added to currently stored devices */
            state.retrievedDevices.fetching = payload.fetching
            if (payload.data) {
                payload.data.forEach(function (device) {
                    device.selected = false
                })
                state.retrievedDevices.data = [...state.retrievedDevices.data, ...payload.data]
            }
            if (payload.error) {
                state.retrievedDevices.error = payload.error
            }
        },
        [ TOGGLE_DEVICE ] (state, id) {
            state.retrievedDevices.data.forEach(function (device) {
                if (device['_id'] === id) {
                    if (device.selected === undefined) {
                        device.selected = true
                        return
                    }
                    device.selected = !device.selected
                }
            })
        },
        [ TOGGLE_DEVICE_ALL ] (state, event) {
            state.retrievedDevices.data.forEach(function (device) {
                device.selected = event.target.checked
            })
        },
        [ TOGGLE_DEVICE_FIELD ] (state, path) {
            state.fields.forEach(function (field) {
                if (field.path === path) {
                    field.selected = !field.selected
                }
            })
        },
        [ TOGGLE_DEVICE_TAG ] (state, path) {
            state.tags.forEach(function (tag) {
                if (tag.path === path) {
                    tag.selected = !tag.selected
                }
            })
        }
    },
    actions: {
        [ FETCH_DEVICES ] ({dispatch, commit}, payload) {
            /* Fetch list of devices for requested page and filtering */
            if (!payload.skip) { payload.skip = 0 }
            /* Getting first page - empty table */
            if (payload.skip === 0) { commit(RESTART_DEVICES) }
            dispatch(REQUEST_API, {
                rule: `api/devices?limit=${payload.limit}&skip=${payload.skip}&fields=${payload.fields}`,
                type: UPDATE_DEVICES
            })
        },
        [ GET_DEVICE ] ({dispatch}, payload) {
            /* Fetch a single device according to requested id */
            if (!payload.deviceId) { return }
            dispatch(REQUEST_API, {
                rule: `api/devices?${payload.deviceId}`,
                type: SET_DEVICE
            })
        },
        [ SAVE_DEVICE_TAGS ] (state, payload) {
            console.log(payload.devices)
            console.log(payload.tags)
        }
    }
}