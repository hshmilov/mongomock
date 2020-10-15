import axiosClient from '@api/axios.js';
import Promise from 'promise';

import _get from 'lodash/get';
import _isEmpty from 'lodash/isEmpty';
import { INIT_USER } from './modules/auth';
import {
  UPDATE_DATA,
  UPDATE_DATA_CONTENT,
  UPDATE_DATA_COUNT,
  UPDATE_DATA_COUNT_QUICK,
  ADD_DATA_VIEW,
  CHANGE_DATA_VIEW,
  UPDATE_DATA_FIELDS,
  UPDATE_DATA_LABELS,
  UPDATE_ADDED_DATA_LABELS,
  UPDATE_REMOVED_DATA_LABELS,
  SELECT_DATA_CURRENT,
  UPDATE_DATA_CURRENT,
  UPDATE_SAVED_DATA_NOTE,
  UPDATE_REMOVED_DATA_NOTE,
  UPDATE_SYSTEM_CONFIG,
  UPDATE_SYSTEM_EXPIRED,
  UPDATE_DATA_HYPERLINKS,
  UPDATE_CUSTOM_DATA,
  UPDATE_DATA_VIEW,
  UPDATE_SYSTEM_DEFAULT_COLUMNS,
  UPDATE_QUERY_INVALID_REFERENCES,
  UPDATE_QUERY_ERROR,
} from './mutations';


/*
    A generic wrapper for requests to server.
    Before request, performs given mutation to initialize error and indicate fetching in process,
    After request, performs given mutation with controls received or error thrown, accordingly

    @param {commit} - Vue action mechanism provides this
    @param payload - An object containing: {
        method: HTTP method for the request [defaulted GET]
        rule: Entry in the API to call, including request parameters, if needed
        controls: Object with controls, for HTTP methods that allow sending it, if needed,
        type: Mutation type to call
    }
 */

export const MAX_GET_SIZE = 2000;
export const REQUEST_API = 'REQUEST_API';
export const requestApi = async ({ commit }, payload) => {
  const {
    type: mutation,
    payload: actionPayload,
    rule,
    data,
    binary,
  } = payload;

  if (!rule) throw new Error('rule not supplied');

  if (mutation) {
    commit(mutation, {
      rule: payload.rule, fetching: true, error: '', ...actionPayload,
    });
  }

  const requestConfig = {
    method: payload.method || 'GET',
    url: payload.rule,
    data,
    responseType: binary ? 'arraybuffer' : 'appliaction/json',
  };

  try {
    const response = await axiosClient(requestConfig);
    if (mutation) {
      commit(mutation, {
        rule,
        fetching: false,
        data: response.data,
        ...actionPayload,
      });
    }
    return response;
  } catch (error) {
    const apiErrorMessage = _get(error, 'response.data.message');
    let errorMessage = apiErrorMessage || error.message;

    if (error.response) {
      if (error.response.status === 401) {
        if (errorMessage !== 'password expired') {
          commit(INIT_USER, { fetching: false, error: errorMessage });
          throw error;
        }
      }
      if (error.response.status >= 500) {
        errorMessage = 'An error occurred. Please contact the Axonius support team.';
      }
    }
    if (mutation) {
      commit(payload.type, {
        rule, fetching: false, error: errorMessage, ...actionPayload,
      });
    }
    throw error;
  }
};

export const getModule = (state, payload) => {
  if (!payload || !payload.module) return null;
  return payload.module.split('/').reduce((moduleState, key) => moduleState[key], state);
};

export const FETCH_DATA_COUNT = 'FETCH_DATA_COUNT';
export const fetchDataCount = async ({ state, dispatch }, payload) => {
  const path = payload.endpoint || payload.module;
  const module = getModule(state, payload);
  if (!module) return;
  const { view } = module;

  module.count.data = undefined;

  if (payload.isExperimentalAPI && ['users', 'devices'].includes(path) && view.query.search !== null) {
    // eslint-disable-next-line consistent-return
    await dispatch(REQUEST_API, {
      rule: `/graphql/search/${path}?term=${view.query.search}&count=True`,
      type: UPDATE_DATA_COUNT,
      payload,
    });
    return;
  }
  // For now we support only /users and /devices 'big queries'
  if (view.query.filter.length > MAX_GET_SIZE && ['users', 'devices'].includes(path)) {
    await dispatch(REQUEST_API, {
      rule: `${path}/count`,
      type: UPDATE_DATA_COUNT,
      method: 'POST',
      data: {
        filter: view.query.filter,
        history: view.historical,
      },
      payload,
    });
    if (!payload.isExperimentalAPI) {
      await dispatch(REQUEST_API, {
        rule: `${path}/count`,
        type: UPDATE_DATA_COUNT_QUICK,
        method: 'POST',
        data: {
          filter: view.query.filter,
          history: view.historical,
          quick: true,
        },
        payload,
      });
    }
  } else {
    const params = [];

    if (view.query) {
      if (view.query.filter) {
        params.push(`filter=${encodeURIComponent(view.query.filter)}`);
      }
      if (view.query.search) {
        params.push(`search=${encodeURIComponent(view.query.search)}`);
      }
    }

    if (payload.isExperimentalAPI) {
      params.push(`experimental=${encodeURIComponent(payload.isExperimentalAPI)}`);
    }

    if (view.historical) {
      params.push(`history=${encodeURIComponent(view.historical)}`);
    }
    if (view.queryStrings) {
      Object.keys(view.queryStrings)
        .filter((item) => view.queryStrings[item])
        .forEach((key) => {
          params.push(`${key}=${view.queryStrings[key]}`);
        });
    }

    dispatch(REQUEST_API, {
      rule: `${path}/count?${params.join('&')}`,
      type: UPDATE_DATA_COUNT,
      payload,
    });
    // if we are using experimental skip "stupid" quick count
    if (!payload.isExperimentalAPI) {
      params.push('quick=True');
      dispatch(REQUEST_API, {
        rule: `${path}/count?${params.join('&')}`,
        type: UPDATE_DATA_COUNT_QUICK,
        payload,
      });
    }
  }
};

const createPostContentRequest = (state, payload) => {
  const module = getModule(state, payload);
  if (!module) return '';
  const { view } = module;

  const params = Object();

  if (payload.skip !== undefined) {
    params.skip = payload.skip;
  }
  if (payload.limit !== undefined) {
    params.limit = payload.limit;
  }
  const fields = payload.fields || _get(view, 'fields', []);
  if (fields.length) {
    // fields is array, we want to format it as string
    // so we are using ${}
    params.fields = `${fields}`;
  }
  const schemaFields = payload.schema_fields || _get(view, 'schema_fields', null);
  if (schemaFields) {
    params.schema_fields = schemaFields;
  }
  if (_get(view, 'query')) {
    if (view.query.filter) {
      params.filter = view.query.filter;
    }
    if (view.query.search) {
      params.search = view.query.search;
    }
  }

  if (view) {
    if (view.historical) {
      params.history = view.historical;
    }
    if (view.colFilters) {
      params.field_filters = view.colFilters;
    }
    if (view.colExcludedAdapters) {
      params.excluded_adapters = view.colExcludedAdapters;
    }
    if (view.queryStrings) {
      Object.keys(view.queryStrings)
        .filter((item) => view.queryStrings[item])
        .forEach((key) => {
          params[key] = view.queryStrings[key];
        });
    }
  }

  if (payload.isExperimentalAPI) {
    params.experimental = payload.isExperimentalAPI;
  }
  // TODO: Not passing expressions because it might reach max URL size
  // if (view.query.expressions) {
  // 	params.push(`expressions=${encodeURI(JSON.stringify(view.query.expressions))}`)
  // }

  if (_get(view, 'sort.field')) {
    params.sort = view.sort.field;
    params.desc = view.sort.desc ? '1' : '0';
  }
  if (payload.isRefresh) {
    params.is_refresh = 1;
  }

  // Compliance
  if (payload.accounts) {
    params.accounts = payload.accounts;
  }
  if (payload.rules) {
    params.rules = payload.rules;
  }
  if (payload.categories) {
    params.categories = payload.categories;
  }
  if (payload.failedOnly) {
    params.failedOnly = payload.failedOnly;
  }

  if (payload.delimiter !== undefined) {
    params.delimiter = payload.delimiter;
  }
  if (payload.maxRows !== undefined) {
    params.max_rows = payload.maxRows;
  }
  params.get_metadata = payload.getMetadata || false;
  params.include_details = payload.includeDetails || true;

  return params;
};

const createContentRequest = (state, payload) => {
  const params = createPostContentRequest(state, payload);
  return Object.keys(params)
    .filter((key) => ['string', 'number', 'boolean'].includes(typeof params[key]))
    .map((key) => `${key}=${encodeURIComponent(params[key])}`).join('&');
};

export const FETCH_DATA_CONTENT = 'FETCH_DATA_CONTENT';
export const fetchDataContent = async ({ state, dispatch }, payload) => {
  const module = getModule(state, payload);
  const path = payload.endpoint || payload.module;
  if (!module) return Promise.reject(new Error('module is required'));

  const getCount = !(payload.getCount === false);

  if (!payload.skip && module.count !== undefined && getCount) {
    await dispatch(FETCH_DATA_COUNT, { module: payload.module, endpoint: payload.endpoint, isExperimentalAPI: payload.isExperimentalAPI });
  }

  const { view } = module;
  if (payload.isExperimentalAPI && ['users', 'devices'].includes(path) && view.query.search !== null) {
    return await dispatch(REQUEST_API, {
      rule: `/graphql/search/${path}?term=${view.query.search}&limit=${payload.limit}&offset=${payload.skip}`,
      type: UPDATE_DATA_CONTENT,
      payload,
    });
  }

  if (!view) {
    return await dispatch(REQUEST_API, {
      rule: `${path}?${createContentRequest(state, payload)}`,
      type: UPDATE_DATA_CONTENT,
      payload,
    });
  }

  if (['users', 'devices'].includes(path)) {
    return await dispatch(REQUEST_API, {
      rule: path,
      method: 'POST',
      data: createPostContentRequest(state, payload),
      type: UPDATE_DATA_CONTENT,
      payload,
    });
  }
  return await dispatch(REQUEST_API, {
    rule: `${path}?${createContentRequest(state, payload)}`,
    type: UPDATE_DATA_CONTENT,
    payload,
  });
};

export const downloadFile = (fileType, response, objName, objSource) => {
  const blob = new Blob([response.data], { type: response.headers['content-type'] });
  const link = document.getElementById('file-auto-download-link');
  link.href = window.URL.createObjectURL(blob);
  const contentDisposition = response.headers['content-disposition'] || '';
  const filenameMatch = contentDisposition.match('filename=(.+)');
  if (filenameMatch && filenameMatch.length > 1) {
    link.download = filenameMatch[1];
  } else {
    const now = new Date();
    const formattedDate = now.toISOString().substr(0, 10);
    const formattedTime = now.toLocaleTimeString('en-US', {
      timeZone: 'Etc/UTC',
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).replace(/:/g, '-');
    const fileSource = fileType === 'csv' ? 'data' : 'report';
    const prefix = objName ? objName.replace(/[\s,-]/g, '_') : objSource || fileSource;
    link.download = `axonius-${prefix}_${formattedDate}T${formattedTime}UTC.${fileType}`;
  }
  link.click();
};

export const FETCH_DATA_CONTENT_CSV = 'FETCH_DATA_CONTENT_CSV';
export const fetchDataContentCSV = ({ state, dispatch }, payload) => dispatch(REQUEST_API, {
  rule: `${payload.endpoint || payload.module}/csv`,
  method: 'POST',
  data: createPostContentRequest(state, payload),
}).then((response) => {
  downloadFile('csv', response, null, payload.source);
});

export const PUBLISH_VIEW = 'PUBLISH_VIEW';
export const publishView = ({ dispatch, commit }, payload) => {
  const {
    name, description, private: is_private, view, tags, predefined, uuid, module,
  } = payload;
  const data = {
    name,
    description,
    private: is_private,
    tags,
    view: {
      query: view.query,
      fields: view.fields,
      sort: view.sort,
      colFilters: view.colFilters,
    },
  };

  return dispatch(REQUEST_API, {
    rule: `${module}/views/${uuid}/publish`,
    method: 'POST',
    data,
  }).then(() => {
    commit(CHANGE_DATA_VIEW, payload);
  });
};

export const SAVE_VIEW = 'SAVE_VIEW';
export const saveView = ({ dispatch, commit }, payload) => {
  const {
    name, description, private: is_private, view, tags, predefined, uuid, module,
  } = payload;
  const data = {
    name,
    description,
    private: is_private,
    tags,
    view: {
      query: view.query,
      fields: view.fields,
      sort: view.sort,
      colFilters: view.colFilters,
      colExcludedAdapters: view.colExcludedAdapters,
    },
  };
  if (predefined) {
    data.predefined = true;
  }
  if (uuid) {
    return dispatch(REQUEST_API, {
      rule: `${module}/views/${uuid}`,
      method: 'POST',
      data,
    }).then(() => {
      commit(CHANGE_DATA_VIEW, payload);
    }).catch((error) => {
      const errorMessage = _get(error, 'response.data.message', '');
      commit(UPDATE_QUERY_ERROR, {
        module, error: errorMessage,
      });
    });
  }
  return dispatch(REQUEST_API, {
    rule: `${module}/views`,
    method: 'PUT',
    data,
  }).then((response) => {
    if (response.status === 200) {
      commit(ADD_DATA_VIEW, {
        module, uuid: response.data, ...data,
      });
      if (!predefined) {
        commit(UPDATE_DATA_VIEW, { module, selectedView: { uuid: response.data } });
      }
    }
  }).catch(console.log.bind(console));
};

export const SAVE_DATA_VIEW = 'SAVE_DATA_VIEW';
export const saveDataView = ({ state, dispatch, commit }, payload) => {
  if (getModule(state, payload)) {
    const newPayload = payload;
    newPayload.view = state[payload.module].view;

    if (_get(newPayload, 'view.query.meta.searchTemplate', false)) {
      delete newPayload.view.query.meta.searchTemplate;
      newPayload.view.query.search = null;
    }
    return saveView({ dispatch, commit }, newPayload);
  }
};

export const FETCH_DATA_FIELDS = 'FETCH_DATA_FIELDS';
export const fetchDataFields = async ({ state, dispatch }, payload) => {
  if (!getModule(state, payload)) {
    return Promise.resolve();
  }
  return dispatch(REQUEST_API, {
    rule: `${payload.module}/fields`,
    type: UPDATE_DATA_FIELDS,
    payload: { module: payload.module },
  });
};

export const LAZY_FETCH_DATA_FIELDS = 'LAZY_FETCH_DATA_FIELDS';
export const lazyFetchDataFields = async ({ dispatch, state }, payload) => {
  const fields = _get(state, `${payload.module}.fields.data`, {});
  if (!_isEmpty(fields)) {
    return Promise.resolve();
  }
  return dispatch(FETCH_DATA_FIELDS, payload);
};

export const FETCH_DATA_HYPERLINKS = 'FETCH_DATA_HYPERLINKS';
export const fetchDataHyperlinks = ({ state, dispatch }, payload) => {
  if (!getModule(state, payload)) return;
  dispatch(REQUEST_API, {
    rule: `${payload.module}/hyperlinks`,
    type: UPDATE_DATA_HYPERLINKS,
    payload: { module: payload.module },
  });
};

export const START_RESEARCH_PHASE = 'START_RESEARCH_PHASE';
export const startResearch = ({ dispatch }) => dispatch(REQUEST_API, {
  rule: 'settings/run_manual_discovery',
  method: 'POST',
});

export const FETCH_DATA_LABELS = 'FETCH_DATA_LABELS';
export const fetchDataLabels = ({ state, dispatch }, payload) => {
  if (!getModule(state, payload)) return;
  dispatch(REQUEST_API, {
    rule: `${payload.module}/labels`,
    type: UPDATE_DATA_LABELS,
    payload: { module: payload.module },
  });
};

export const ADD_DATA_LABELS = 'ADD_DATA_LABELS';
export const addDataLabels = ({ state, dispatch }, payload) => {
  const moduleState = getModule(state, payload);
  if (!moduleState) return;
  if (!payload.data || !payload.data.entities || !payload.data.labels || !payload.data.labels.length) {
    return;
  }
  payload.data.filter = moduleState.view.query.filter;
  return dispatch(REQUEST_API, {
    rule: `${payload.module}/labels`,
    method: 'POST',
    data: payload.data,
    type: UPDATE_ADDED_DATA_LABELS,
    payload,
  });
};

export const REMOVE_DATA_LABELS = 'REMOVE_DATA_LABELS';
export const removeDataLabels = ({ state, dispatch }, payload) => {
  const moduleState = getModule(state, payload);
  if (!moduleState) return;
  if (!payload.data || !payload.data.entities || !payload.data.labels || !payload.data.labels.length) {
    return;
  }
  payload.data.filter = moduleState.view.query.filter;
  return dispatch(REQUEST_API, {
    rule: `${payload.module}/labels`,
    method: 'DELETE',
    data: payload.data,
    type: UPDATE_REMOVED_DATA_LABELS,
    payload,
  });
};

export const DELETE_DATA = 'DELETE_DATA';
export const deleteData = ({ state, dispatch }, payload) => {
  const moduleState = getModule(state, payload);
  if (!moduleState || !payload.selection) return;

  return dispatch(REQUEST_API, {
    rule: `${payload.module}?filter=${encodeURIComponent(moduleState.view.query.filter)}`,
    method: 'DELETE',
    data: payload.selection,
  });
};

export const DELETE_VIEW_DATA = 'DELETE_VIEW_DATA';
export const deleteViewData = ({ dispatch }, payload) => {
  if (!payload.selection) return;

  return dispatch(REQUEST_API, {
    rule: `${payload.module}/${payload.selection}`,
    method: 'DELETE',
    data: { private: payload.private },
  });
};

export const LINK_DATA = 'LINK_DATA';
export const linkData = ({ state, dispatch }, payload) => {
  const moduleState = getModule(state, payload);
  if (!moduleState || !payload.data) return;
  payload.data.filter = moduleState.view.query.filter;
  return dispatch(REQUEST_API, {
    rule: `${payload.module}/manual_link`,
    method: 'POST',
    data: payload.data,
  });
};

export const UNLINK_DATA = 'UNLINK_DATA';
export const unlinkData = ({ state, dispatch }, payload) => {
  const moduleState = getModule(state, payload);
  if (!moduleState || !payload.data) return;
  payload.data.filter = moduleState.view.query.filter;
  return dispatch(REQUEST_API, {
    rule: `${payload.module}/manual_unlink`,
    method: 'POST',
    data: payload.data,
  });
};

export const ENFORCE_DATA = 'ENFORCE_DATA';
export const enforceData = ({ state, dispatch }, payload) => {
  const moduleState = getModule(state, payload);
  if (!moduleState || !payload.data) return;
  payload.data.filter = moduleState.view.query.filter;
  return dispatch(REQUEST_API, {
    rule: `${payload.module}/enforce`,
    method: 'POST',
    data: payload.data,
  });
};

export const FETCH_DATA_CURRENT = 'FETCH_DATA_CURRENT';
export const fetchDataCurrent = ({ state, dispatch, commit }, payload) => {
  if (!getModule(state, payload)) return;
  commit(SELECT_DATA_CURRENT, payload);

  let rule = `${payload.module}/${payload.id}`;
  if (payload.history) {
    rule += `?history=${encodeURIComponent(payload.history)}&api_format=false`;
  } else {
    rule += '?api_format=false';
  }
  return dispatch(REQUEST_API, {
    rule,
    type: UPDATE_DATA_CURRENT,
    payload: {
      module: `${payload.module}/current`,
    },
  });
};

export const FETCH_DATA_CURRENT_TASKS = 'FETCH_DATA_CURRENT_TASKS';
export const fetchDataCurrentTasks = ({ state, dispatch, commit }, payload) => {
  if (!getModule(state, payload)) return;

  let rule = `${payload.module}/${payload.id}/tasks`;
  if (payload.history) {
    rule += `?history=${encodeURIComponent(payload.history)}`;
  }
  return dispatch(REQUEST_API, {
    rule,
    type: UPDATE_DATA,
    payload: {
      module: `${payload.module}/current/tasks`,
    },
  });
};

export const SAVE_DATA_NOTE = 'SAVE_DATA_NOTE';
export const saveDataNote = ({ state, dispatch }, payload) => {
  if (!getModule(state, payload)) return;
  if (!payload.entityId) return;
  let rule = `${payload.module}/${payload.entityId}/notes`;
  let method = 'PUT';
  if (payload.noteId) {
    rule = `${rule}/${payload.noteId}`;
    method = 'POST';
  }
  return dispatch(REQUEST_API, {
    rule,
    method,
    data: {
      note: payload.note,
    },
    type: UPDATE_SAVED_DATA_NOTE,
    payload,
  });
};

export const REMOVE_DATA_NOTE = 'REMOVE_DATA_NOTE';
export const removeDataNote = ({ state, dispatch }, payload) => {
  if (!getModule(state, payload)) return;
  if (!payload.entityId || !payload.noteIdList) return;
  return dispatch(REQUEST_API, {
    rule: `${payload.module}/${payload.entityId}/notes`,
    method: 'DELETE',
    data: payload.noteIdList,
    type: UPDATE_REMOVED_DATA_NOTE,
    payload,
  });
};

export const RUN_ACTION = 'RUN_ACTION';
export const runAction = ({ state, dispatch }, payload) => {
  if (!payload || !payload.type || !payload.data) {
    return;
  }
  payload.data.filter = moduleState.view.query.filter;
  return dispatch(REQUEST_API, {
    rule: `actions/${payload.type}`,
    method: 'POST',
    data: payload.data,
  });
};

export const STOP_RESEARCH_PHASE = 'STOP_RESEARCH_PHASE';
export const stopResearch = ({ dispatch }) => dispatch(REQUEST_API, {
  rule: 'settings/stop_research_phase',
  method: 'POST',
});

export const FETCH_SYSTEM_CONFIG = 'FETCH_SYSTEM_CONFIG';
export const fetchSystemConfig = ({ dispatch }) => dispatch(REQUEST_API, {
  rule: 'settings',
  type: UPDATE_SYSTEM_CONFIG,
});

export const FETCH_SYSTEM_EXPIRED = 'FETCH_SYSTEM_EXPIRED';
export const fetchSystemExpired = ({ dispatch }) => dispatch(REQUEST_API, {
  rule: 'system/expired',
  type: UPDATE_SYSTEM_EXPIRED,
});

export const SAVE_CUSTOM_DATA = 'SAVE_CUSTOM_DATA';
export const saveCustomData = ({ state, dispatch }, payload) => {
  const module = getModule(state, payload);
  if (!module) return;
  payload.data.id = 'unique';
  return dispatch(REQUEST_API, {
    rule: `${payload.module}/custom`,
    method: 'POST',
    data: {
      selection: payload.selection,
      data: payload.data,
      filter: module.view.query.filter,
    },
    type: UPDATE_CUSTOM_DATA,
    payload,
  });
};

export const GET_ENVIRONMENT_NAME = 'GET_ENVIRONMENT_NAME';
export const getEnvironmentName = ({ dispatch }) => dispatch(REQUEST_API, {
  rule: 'get_environment_name',
  method: 'GET',
});

export const GET_TUNNEL_STATUS = 'GET_TUNNEL_STATUS';
export const getTunnelStatus = ({ dispatch }) => dispatch(REQUEST_API, {
  rule: 'tunnel/get_status',
  method: 'GET',
});

export const GET_TUNNEL_EMAILS_LIST = 'GET_TUNNEL_EMAILS_LIST';
export const getTunnelEmailsList = ({ dispatch }) => dispatch(REQUEST_API, {
  rule: 'tunnel/emails_list',
  method: 'GET',
});

export const SAVE_TUNNEL_EMAILS_LIST = 'SAVE_TUNNEL_EMAILS_LIST';
export const saveTunnelEmailsList = ({ state, dispatch }, payload) => dispatch(REQUEST_API, {
  rule: 'tunnel/emails_list',
  method: 'POST',
  data: payload,
});

export const GET_TUNNEL_PROXY_SETTINGS = 'GET_TUNNEL_PROXY_SETTINGS';
export const getTunnelProxySettings = ({ dispatch }) => dispatch(REQUEST_API, {
  rule: 'tunnel/proxy_settings',
  method: 'GET',
});

export const SAVE_TUNNEL_PROXY_SETTINGS = 'SAVE_TUNNEL_PROXY_SETTINGS';
export const saveTunnelProxySettings = ({ state, dispatch }, payload) => dispatch(REQUEST_API, {
  rule: 'tunnel/proxy_settings',
  method: 'POST',
  data: payload,
});

export const SAVE_SYSTEM_DEFAULT_COLUMNS = 'SAVE_SYSTEM_DEFAULT_COLUMNS';
export const saveSystemDefaultColumns = ({ dispatch, commit }, payload) => {
  const data = {
    [payload.module]: {
      table_columns: {
        [payload.columnsGroupName]: payload.fields,
      },
    },
  };
  return dispatch(REQUEST_API, {
    rule: 'settings/system_default_columns',
    method: 'POST',
    data,
  }).then(() => {
    commit(UPDATE_SYSTEM_DEFAULT_COLUMNS, payload);
  });
};

export const FETCH_QUERY_INVALID_REFERENCES = 'FETCH_QUERY_INVALID_REFERENCES';
export const fetchInvalidReferences = ({ state, dispatch, commit }, payload) => {
  if (!getModule(state, payload)) return;

  const rule = `${payload.module}/views/references/${payload.uuid}`;
  return dispatch(REQUEST_API, {
    rule,
  }).then((res) => {
    let references = [];
    if (res && res.status === 200) {
      references = res.data;
    }
    commit(UPDATE_QUERY_INVALID_REFERENCES, {
      module: payload.module,
      uuid: payload.uuid,
      validReferences: references,
    });
  });
};
