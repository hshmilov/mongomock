export const RESET_USERS_STATE = 'REEST_USERS_STATE';

const getDefaultState = () => ({
  content: { data: [], fetching: false, error: '' },

  count: { data: 0, fetching: false, error: '' },

  view: {
    page: 0,
    fields: [],
    coloumnSizes: [],
    query: {
      filter: '', expressions: [], search: '',
    },
    sort: {
      field: '', desc: true,
    },
    historical: null,
    colFilters: {},
    filterColumnActive: false,
  },

  details: { data: {}, fetching: false, error: '' },

  fields: { data: [], fetching: false, error: '' },

  hyperlinks: { data: [], fetching: false, error: '' },

  views: {
    saved: {
      content: {
        data: [], fetching: false, error: '', rule: '',
      },
      count: { data: 0, fetching: false, error: '' },
      view: {
        page: 0,
        pageSize: 20,
        query: {
          filter: '', expressions: [], search: '',
        },
        sort: {
          field: '', desc: true,
        },
      },
    },
    history: {
      content: {
        data: [], fetching: false, error: '', rule: '',
      },
    },
  },

  labels: { data: false, fetching: false, error: '' },

  current: {
    id: '',

    fetching: false,
    data: {},
    error: '',

    tasks: {
      fetching: false,
      data: [],
      error: '',
      view: {
        page: 0,
        pageSize: 20,
        columnSizes: [],
        query: {
          filter: '', expressions: [],
        },
        sort: {
          field: 'uuid', desc: true,
        },
      },
    },
  },
});

export const users = {
  state: getDefaultState(),
  mutations: {
    [RESET_USERS_STATE](state) {
      Object.assign(state, getDefaultState());
    },
  },
};
