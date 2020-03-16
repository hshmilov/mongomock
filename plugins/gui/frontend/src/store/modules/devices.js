export const SET_MERGED_DATA_BY_ID = 'SET_MERGED_DATA_BY_ID';
export const RESET_DEVICES_MERGED_DATA_BY_ID = 'RESET_DEVICES_MERGED_DATA_BY_ID';
export const RESET_DEVICES_STATE = 'RESET_DEVICES_STATE'

const getDefaultState = () => {
  return {
    content: {
      data: [], fetching: false, error: '', rule: '',
    },

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
      colFilters: {},
      historical: null,
    },

    details: { data: {}, fetching: false, error: '' },

    fields: { data: {}, fetching: false, error: '' },

    hyperlinks: { data: [], fetching: false, error: '' },

    views: {
      saved: {
        content: {
          data: [],
          fetching: false,
          error: '',
          rule: '',
        },
        count: { data: 0, fetching: false, error: '' },
        view: {
          page: 0,
          pageSize: 20,
          query: {
            filter: '', expressions: [], search: '',
          },
          sort: {
            field: 'last_updated', desc: true,
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
            field: 'recipe_name', desc: true,
          },
        },
      },
    },
    mergedDataById: {},
  };
};

export const devices = {
  state: getDefaultState(),
  getters: {
    getMergedDataById: (state) => (id, name) => state.mergedDataById[`${id}__${name}`],
  },
  mutations: {
    [SET_MERGED_DATA_BY_ID](state, payload) {
      // eslint-disable-next-line no-param-reassign
      state.mergedDataById[`${payload.id}__${payload.schema.name}`] = payload.mergedData;
    },
    [RESET_DEVICES_MERGED_DATA_BY_ID](state) {
      // eslint-disable-next-line no-param-reassign
      state.mergedDataById = {};
    },
    [RESET_DEVICES_STATE](state) {
      Object.assign(state, getDefaultState());
    },
  },
};
