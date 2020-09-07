import { REQUEST_API } from '../actions';

export const FETCH_TASK = 'FETCH_TASK';
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
        field: 'started_at', desc: true,
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
  },
};
