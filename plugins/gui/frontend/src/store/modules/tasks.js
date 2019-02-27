import { REQUEST_API } from '../actions'

export const FETCH_TASK = 'FETCH_TASK'
export const SET_TASK = 'SET_TASK'

export const tasks = {
    state: {
        /* Tasks DataTable State */
        content: { data: [], fetching: false, error: ''},
        count: { data: 0, fetching: false, error: ''},
        view: {
            page: 0, pageSize: 20, fields: [
                'success_rate', 'enforcement', 'main', 'success', 'failure', 'post',
                'trigger_view', 'started_at', 'finished_at'
            ], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
        },
        fields: {
            data: {
                generic: [{
                    name: 'success_rate', title: 'Successful / Total', type: 'string'
                }, {
                    name: 'enforcement', title: 'Name', type: 'string'
                }, {
                    name: 'main', title: 'Main Action', type: 'string'
                }, {
                    name: 'trigger_view', title: 'Trigger Query Name', type: 'string'
                }, {
                    name: 'started_at', title: 'Started', type: 'string', format: 'date-time'
                }, {
                    name: 'finished_at', title: 'Completed', type: 'string', format: 'date-time'
                }]
            }
        },

        /* Data of Task currently being views */
        current: { fetching: false, data: { }, error: '' }
    },
    mutations: {
        [ SET_TASK ] (state, taskData) {
            /*
                Set given data, as Task in the handle
             */
            state.current.data = { ...taskData }
        }
    },
    actions: {
        [ FETCH_TASK ] ({dispatch, commit}, taskId) {
            /*
                Ask server for a complete, specific task, with all details of the run
             */
            return dispatch(REQUEST_API, {
                rule: `tasks/${taskId}`
            }).then((response) => {
                if (response.status === 200 && response.data) {
                    commit(SET_TASK, response.data)
                }
            })
        }
    }
}