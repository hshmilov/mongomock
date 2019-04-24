import { REQUEST_API } from '../actions'

export const FETCH_TASK = 'FETCH_TASK'
export const SET_TASK = 'SET_TASK'

export const tasks = {
    state: {
        /* Tasks DataTable State */
        content: { data: [], fetching: false, error: ''},
        count: { data: 0, fetching: false, error: ''},
        view: {
            page: 0, pageSize: 20, coloumnSizes: [], query: {
                filter: '', expressions: []
            }, sort: {
                field: '', desc: true
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