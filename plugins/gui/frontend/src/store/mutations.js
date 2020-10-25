import _pickBy from 'lodash/pickBy';
import _isEmpty from 'lodash/isEmpty';
import _toString from 'lodash/toString';
import _get from 'lodash/get';
import { getModule } from './actions';
import { pluginMeta } from '../constants/plugin_meta';
import { initCustomData } from '../constants/entities';

export const TOGGLE_SIDEBAR = 'TOGGLE_SIDEBAR';
export const toggleSidebar = (state) => {
  state.interaction.collapseSidebar = !state.interaction.collapseSidebar;
};

export const UPDATE_DATA = 'UPDATE_DATA';
export const updateData = (state, payload) => {
  const moduleState = getModule(state, payload);
  moduleState.fetching = payload.fetching;
  moduleState.error = payload.error;
  if (payload.data) {
    moduleState.data = payload.data;
  }
};

export const UPDATE_LANGUAGE = 'UPDATE_LANGUAGE';
export const updateLanguage = (state, payload) => {
  state.interaction.language = payload;
};

export const UPDATE_BRANCH = 'UPDATE_BRANCH';
export const updateBranch = (state, payload) => {
  state.interaction.branch = payload;
};

function clearUrlFromQuick(url) {
  const regex = /&?quick=(False|True)/gi;
  return url.replace(regex, '');
}

export const UPDATE_DATA_COUNT_QUICK = 'UPDATE_DATA_COUNT_QUICK';
export const updateDataCountQuick = (state, payload) => {
  const module = getModule(state, payload);
  if (!module) return;
  const { count } = module;
  if (!payload.fetching && count.rule !== clearUrlFromQuick(payload.rule)) {
    return;
  }

  count.fetching = payload.fetching;
  count.error = payload.error;
  count.rule = clearUrlFromQuick(payload.rule);

  if (payload.data !== undefined) {
    if (count.data == undefined) {
      count.data = payload.data;
      count.data_to_show = payload.data;
      if (payload.data == '1000') {
        count.data_to_show = 'Loading...';
      }
    }
  }
};

export const UPDATE_DATA_COUNT = 'UPDATE_DATA_COUNT';
export const updateDataCount = (state, payload) => {
  const module = getModule(state, payload);
  if (!module) return;
  const { count } = module;
  if (!payload.fetching && count.rule !== payload.rule) {
    return;
  }

  count.fetching = payload.fetching;
  count.error = payload.error;
  count.rule = payload.rule;

  if (payload.isExperimentalAPI && payload.data !== undefined) {
    const [data] = payload.data.data[`${payload.module}_aggregate`];
    const { count: resCount } = data;
    const strCountValue = _toString(resCount);
    count.data = strCountValue;
    count.data_to_show = strCountValue;
    return;
  }
  if (payload.data !== undefined) {
    count.data = payload.data;
    count.data_to_show = payload.data;
  }
};

export const UPDATE_DATA_CONTENT = 'UPDATE_DATA_CONTENT';
export const updateDataContent = (state, payload) => {
  const module = getModule(state, payload);
  if (!module) return;
  const { content } = module;
  if (!payload.fetching && content.rule !== payload.rule) {
    return;
  }
  content.fetching = payload.fetching;
  content.rule = payload.rule;
  content.error = payload.error;
  if (!payload.data) {
    return;
  }

  let payloadData = payload.data;
  if (payloadData.cache_last_updated) {
    // Cached result.
    content.cache_last_updated = payloadData.cache_last_updated;
    payloadData = payload.data.entities;
  }

  if (payload.isExperimentalAPI && payloadData.data !== undefined) {
    // eslint-disable-next-line no-underscore-dangle
    payloadData = payload.data.data[payload.module].map((item) => (item._compatibilityAPI || {}));
  }
  if (!payload.skip) {
    content.data = payloadData;
    if (module.count !== undefined && module.count.data > content.data.length) {
      content.data[module.count.data - 1] = null;
    }
  } else if (payloadData.length) {
    content.data.splice(payload.skip, payloadData.length, ...payloadData);
  }
};

export const UPDATE_DATA_VIEW = 'UPDATE_DATA_VIEW';
export const updateDataView = (state, payload) => {
  const module = getModule(state, payload);
  if (!module) return;
  if (payload.view) {
    module.view = { ...module.view, ...payload.view };
    if (payload.view.fields) {
      module.view.colFilters = _pickBy(module.view.colFilters, (value, key) => payload.view.fields.includes(key));
    }
  }
  if (payload.selectedView !== undefined) {
    state[payload.module] = { ...module, selectedView: payload.selectedView };
  } else if (payload.name !== undefined) {
    const selectedView = module.views.saved.content.data.find((view) => view.name === payload.name)
      || null;
    state[payload.module] = { ...module, selectedView };
  }
};

export const UPDATE_DATA_VIEW_FILTER = 'UPDATE_DATA_VIEW_FILTER';
export const updateDataViewFilter = (state, payload) => {
  const module = getModule(state, payload);
  if (!module) return;

  const colFilters = { ...module.view.colFilters };

  if (_isEmpty(payload.filters)) {
    delete colFilters[payload.fieldName];
  } else {
    colFilters[payload.fieldName] = payload.filters;
  }

  module.view.colFilters = colFilters;


  const colExcludedAdapters = { ...module.view.colExcludedAdapters };

  if (_isEmpty(payload.excludeAdapters)) {
    delete colExcludedAdapters[payload.fieldName];
  } else {
    colExcludedAdapters[payload.fieldName] = payload.excludeAdapters;
  }

  module.view.colExcludedAdapters = colExcludedAdapters;

};

export const CLEAR_DATA_VIEW_FILTERS = 'CLEAR_DATA_VIEW_FILTERS';
export const clearDataViewFilter = (state, payload) => {
  const module = getModule(state, payload);
  if (!module) return;
  module.view.colFilters = {};
  module.view.colExcludedAdapters = {};
};

export const ADD_DATA_VIEW = 'ADD_DATA_VIEW';
export const addDataView = (state, payload) => {
  if (!getModule(state, payload)) return;
  const views = state[payload.module].views.saved.content;
  if (!views.data) views.data = [];
  views.data = [{
    uuid: payload.uuid,
    name: payload.name,
    view: payload.view,
    description: payload.description,
    private: payload.private,
  }, ...views.data.filter((item) => item.name !== payload.name)];
};

export const CHANGE_DATA_VIEW = 'CHANGE_DATA_VIEW';
export const changeDataView = (state, payload) => {
  const stateModule = getModule(state, payload);
  if (!stateModule) return;
  const views = stateModule.views.saved.content;
  if (!views || !views.data || !views.data.length) return;
  views.data = views.data.map((item) => {
    // because of the way we handle paging, the last item in this array might be null
    if (item && (item.uuid === payload.uuid)) {
      const {
        name, description, view, tags, private: is_private,
      } = payload;
      return {
        ...item,
        name,
        description,
        view,
        tags,
        private: is_private,
        last_updated: new Date().toGMTString(),
      };
    }
    return item;
  });
};

export const UPDATE_REMOVED_DATA_VIEW = 'UPDATE_REMOVED_DATA_VIEW';
export const updateRemovedDataView = (state, payload) => {
  const stateModule = getModule(state, payload);
  if (!stateModule) return;
  const filterSelectedQueries = (query) => !payload.selection.includes(query.uuid);
  stateModule.content.data = stateModule.content.data.filter(filterSelectedQueries);
};

export const UPDATE_DATA_FIELDS = 'UPDATE_DATA_FIELDS';
export const updateDataFields = (state, payload) => {
  if (!getModule(state, payload)) return;
  const { fields } = state[payload.module];
  fields.fetching = payload.fetching;
  fields.error = payload.error;
  if (payload.data) {
    fields.data = { generic: payload.data.generic, specific: {}, schema: payload.data.schema };
    Object.keys(payload.data.specific).forEach((name) => {
      const pluginMetadata = pluginMeta[name];
      if (!pluginMetadata) return;
      fields.data.specific[name] = payload.data.specific[name];
      fields.data.generic[0].items.enum.push({ name, title: pluginMetadata.title || name });
    });
    const sortByTitle = (first, second) => ((first.title < second.title) ? -1 : 1);
    fields.data.generic[0].items.enum.sort(sortByTitle);
  }
};

export const UPDATE_DATA_HYPERLINKS = 'UPDATE_DATA_HYPERLINKS';
export const updateDataHyperlinks = (state, payload) => {
  if (!getModule(state, payload)) return;
  const { hyperlinks } = state[payload.module];
  hyperlinks.fetching = payload.fetching;
  hyperlinks.error = payload.error;
  if (payload.data) {
    hyperlinks.data = payload.data;
  }
};


export const UPDATE_DATA_LABELS = 'UPDATE_DATA_LABELS';
export const updateDataLabels = (state, payload) => {
  if (!getModule(state, payload)) return;
  const labels = state[payload.module].labels || {};
  labels.fetching = payload.fetching;
  labels.error = payload.error;
  if (payload.data) {
    labels.data = payload.data.map((label) => ({ name: label, title: label }));
  }
};

const isEntitySelected = (id, entities) => (entities.include && entities.ids.includes(id))
  || (!entities.include && !entities.ids.includes(id));

export const UPDATE_ADDED_DATA_LABELS = 'UPDATE_ADDED_DATA_LABELS';
export const updateAddedDataLabels = (state, payload) => {
  const module = getModule(state, payload);
  const { data } = payload;
  module.labels.data = module.labels.data
    .filter((label) => !data.labels.includes(label.name))
    .concat(data.labels.map((label) => ({ name: label, title: label })));

  module.content.data = module.content.data.map((entity) => {
    if (!entity || !isEntitySelected(entity.internal_axon_id, data.entities)) {
      return entity;
    }
    const labels = entity.labels ? entity.labels : [];
    return {
      ...entity, labels: Array.from(new Set([...labels, ...data.labels])),
    };
  });

  const currentData = module.current.data;
  if (module.current.id && isEntitySelected(module.current.id, data.entities)) {
    module.current.data = {
      ...currentData,
      labels: Array.from(new Set([...currentData.labels, ...data.labels])),
    };
  }
};

export const UPDATE_REMOVED_DATA_LABELS = 'UPDATE_REMOVED_DATA_LABELS';
export const updateRemovedDataLabels = (state, payload) => {
  const module = getModule(state, payload);
  const { data } = payload;
  module.labels.data = module.labels.data.filter((label) => {
    if (!data.labels.includes(label.name)) {
      return true;
    }
    const entityContainsLabel = (entity) => (!entity.labels || entity.labels.includes(label.name));
    return module.content.data.some(entityContainsLabel);
  });

  module.content.data = module.content.data.map((entity) => {
    if (!entity || !isEntitySelected(entity.internal_axon_id, data.entities) || !entity.labels) {
      return entity;
    }
    return {
      ...entity, labels: entity.labels.filter((label) => !data.labels.includes(label)),
    };
  });

  const currentData = module.current.data;
  const currentId = module.current.id;
  if (currentId && isEntitySelected(currentId, data.entities) && currentData.labels) {
    module.current.data = {
      ...currentData,
      labels: currentData.labels.filter((label) => !data.labels.includes(label)),
    };
  }
};

export const SELECT_DATA_CURRENT = 'SELECT_DATA_CURRENT';
export const selectDataCurrent = (state, payload) => {
  const module = getModule(state, payload);
  module.current.id = payload.id;
  if (!payload.id) {
    module.current.data = {};
    module.current.tasks.data = [];
  }
};

export const UPDATE_DATA_CURRENT = 'UPDATE_DATA_CURRENT';
export const updateDataCurrent = (state, payload) => {
  const moduleState = getModule(state, payload);
  moduleState.fetching = payload.fetching;
  moduleState.error = payload.error;
  if (payload.data) {
    moduleState.data = {
      ...payload.data,
      advanced: payload.data.advanced.map((item) => ({
        data: item.data,
        view: {
          page: 0,
          pageSize: 20,
          coloumnSizes: [],
          query: {
            filter: '', expressions: [], search: '',
          },
          sort: {
            field: '', desc: true,
          },
          historical: null,
        },
        schema: item.schema,
      }), {}),
    };
  }
};

export const UPDATE_SAVED_DATA_NOTE = 'UPDATE_SAVED_DATA_NOTE';
export const updateSavedDataNote = (state, payload) => {
  const module = getModule(state, payload);
  if (!payload.fetching && !payload.error) {
    let notes = module.current.data.data.find((item) => item.name === 'Notes');
    if (payload.noteId) {
      notes.data = notes.data.map((item) => {
        if (item.uuid === payload.noteId) {
          return { ...item, ...payload.data };
        }
        return item;
      });
    } else {
      if (!notes) {
        notes = {
          name: 'Notes', data: [],
        };
        module.current.data.data.push(notes);
      }
      notes.data.push(payload.data);
    }
  }
};

export const UPDATE_REMOVED_DATA_NOTE = 'UPDATE_REMOVED_DATA_NOTE';
export const updateRemovedDataNote = (state, payload) => {
  const module = getModule(state, payload);
  if (!payload.fetching && !payload.error) {
    const notes = module.current.data.data.find((item) => item.name === 'Notes');
    notes.data = notes.data.filter((note) => !payload.noteIdList.includes(note.uuid));
  }
};

export const UPDATE_SYSTEM_CONFIG = 'UPDATE_SYSTEM_CONFIG';
export const updateSystemConfig = (state, payload) => {
  state.configuration.fetching = payload.fetching;
  state.configuration.error = payload.error;
  if (payload.data) {
    state.configuration.data = { ...state.configuration.data, ...payload.data };
  }
};

export const UPDATE_SYSTEM_EXPIRED = 'UPDATE_SYSTEM_EXPIRED';
export const updateSystemExpired = (state, payload) => {
  state.expired.fetching = payload.fetching;
  state.expired.error = payload.error;
  if (payload.data !== undefined) {
    state.expired.data = payload.data;
  }
};

export const UPDATE_CUSTOM_DATA = 'UPDATE_CUSTOM_DATA';
export const updateCustomData = (state, payload) => {
  const module = getModule(state, payload);
  if (!payload.fetching || !module.current.data.adapters) return;

  const prepareCustomFieldName = (name) => (`custom_${name.split(' ').join('_').toLowerCase()}`);

  const guiAdapter = module.current.data.adapters.find((item) => item.name === 'gui');
  const data = Object.entries(payload.data).reduce((map, [fieldName, itemValue]) => {
    if (fieldName === 'id') return map;
    const [key, value] = itemValue.predefined
      ? [fieldName, itemValue.value]
      : [prepareCustomFieldName(fieldName), itemValue];
    return { ...map, [key]: value };
  }, {});
  if (guiAdapter) {
    guiAdapter.data = data;
  } else {
    module.current.data.adapters.push({
      ...initCustomData(payload.module),
      data,
    });
  }

  const { basic } = module.current.data;

  const trimName = (name) => name.replace(/(adapters_data|specific_data)\.(gui|data)\./g, '');

  const genericFieldNames = module.fields.data.generic.map((field) => field.name);


  const customFields = () => {
    if (!module.fields.data.specific.gui) {
      return module.fields.data.generic;
    }
    return [...module.fields.data.generic,
      ...module.fields.data.specific.gui
        .filter((field) => !genericFieldNames.includes(field.name))];
  };

  const schemaFields = customFields()
    .reduce((map, field) => {
      map[trimName(field.name)] = field;
      return map;
    }, {});

  Object.entries(payload.data).forEach(([fieldName, fieldValue]) => {
    const key = fieldValue.predefined ? fieldName : `custom_${fieldName}`;
    if (!schemaFields[key]) return;

    const value = fieldValue.predefined ? fieldValue.value : fieldValue;
    const fullPath = `specific_data.data.${key}`;
    const basicField = basic[`specific_data.data.${fieldName}`];

    if (Array.isArray(basicField)) {
      if (!basicField) {
        basic[fullPath] = [];
      }
      if (fieldValue.isNew) {
        basicField.push(value);
      } else {
        basicField[basicField.length - 1] = value;
      }
    } else if (basic[fullPath]) {
      basic[fullPath] = [basicField, value];
    } else {
      basic[fullPath] = value;
    }
  });
};

export const SHOW_TOASTER_MESSAGE = 'SHOW_TOASTER_MESSAGE';
export const showToasterMessage = (state, { message, timeout }) => {
  state.toast.message = message;
  if (timeout !== undefined) {
    state.toast.timeout = timeout;
  }
};

export const REMOVE_TOASTER = 'REMOVE_TOASTER';
export const removeToaster = (state) => {
  state.toast.message = '';
};

export const UPDATE_FOOTER_MESSAGE = 'UPDATE_FOOTER_MESSAGE';
export const updateFooterMessage = (state, payload) => {
  state.footer.message = payload;
};

export const UPDATE_SYSTEM_DEFAULT_COLUMNS = 'UPDATE_SYSTEM_DEFAULT_COLUMNS';
export const updateSystemDefaultColumns = (state, payload) => {
  if (_get(state, `configuration.data.defaults.system_columns.${payload.module}`, undefined)) {
    state.configuration.data.defaults.system_columns[payload.module]
      .table_columns[payload.columnsGroupName] = payload.fields;
  } else {
    state.configuration.data.defaults.system_columns[payload.module] = {
      table_columns: { [payload.columnsGroupName]: payload.fields },
    };
  }
};

export const UPDATE_QUERY_INVALID_REFERENCES = 'UPDATE_QUERY_INVALID_REFERENCES';
export const updateQueryInvalidReferences = (state, payload) => {
  state[payload.module].view = {
    ...state[payload.module].view,
    validReferences: {
      [payload.uuid]: payload.validReferences,
    },
  };
};

export const UPDATE_QUERY_ERROR = 'UPDATE_QUERY_ERROR';
export const updateQueryError = (state, payload) => {
  const module = getModule(state, payload);
  if (!module) return;
  const { content } = module;
  content.error = payload.error;
};
