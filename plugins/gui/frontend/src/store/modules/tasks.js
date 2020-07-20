import { FETCH_DATA_CONTENT, REQUEST_API } from '../actions';

export const FETCH_TASK = 'FETCH_TASK';
export const FETCH_ALL_TASKS = 'FETCH_ALL_TASKS';
export const UPDATE_TASK = 'UPDATE_TASK';

export const tasks = {
  state: {
    /* Tasks DataTable State */
    content: { data: [], fetching: false, error: '' },
    count: { data: 0, fetching: false, error: '' },
    view: {
      page: 0,
      pageSize: 20,
      coloumnSizes: [],
      query: {
        filter: '', expressions: [],
      },
      sort: {
        field: '', desc: true,
      },
    },

    /* Data of Task currently being views */
    current: { fetching: false, data: { }, error: '' },
  },
  mutations: {
    [UPDATE_TASK](state, payload) {
      /*
       Set given data, as Task in the handle
      */
      state.current.fetching = payload.fetching;
      state.current.error = payload.error;
      if (payload.data) {
        state.current.data = { ...payload.data };
      }
    },
  },
  actions: {
    [FETCH_TASK]({ dispatch }, taskId) {
      /*
        Ask server for a complete, specific task, with all details of the run
      */
      return dispatch(REQUEST_API, {
        rule: `enforcements/tasks/${taskId}`,
        type: UPDATE_TASK,
      });
    },
    [FETCH_ALL_TASKS]({ dispatch }) {
      /*
        Ask server for all complete tasks, with all details of the run
      */
      return dispatch(FETCH_DATA_CONTENT, {
        module: 'tasks',
        endpoint: 'enforcements/tasks',
        skip: 0,
      });
    },
  },
};
