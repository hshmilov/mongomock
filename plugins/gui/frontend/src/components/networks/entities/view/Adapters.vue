<template>
  <div class="x-entity-adapters">
    <XTabs :vertical="true">
      <XTab
        v-for="(item, i) in sortedSpecificData"
        :id="item.id"
        :key="i"
        :selected="!i"
        :disabled="item.outdated"
        :title="item.pretty_name || item.plugin_name"
        :logo="`adapters/${item.plugin_name}`"
      >
        <div class="header">
          <div class="header__source">
            <template v-if="item.client_used">
              <span class="data_from">Data From: </span>{{ item.connectionLabel || item.client_used }}
            </template>
          </div>
          <XButton
            v-if="isGuiAdapterData(item)"
            type="primary"
            :disabled="userCannotEditDevices"
            @click="editFields"
          >Edit Fields</XButton>
          <XButton
            v-else
            type="link"
            @click="toggleView"
          >View {{ viewBasic? 'Advanced': 'Basic' }}</XButton>
        </div>
        <XList
          v-if="viewBasic || isGuiAdapterData(item)"
          :data="genericSchema && item"
          :schema="adapterSchema(item.plugin_name)"
        />
        <JsonView
          v-else
          :data="item.data.raw"
          root-key="raw"
          :max-depth="6"
        />
      </XTab>
    </XTabs>
    <XModal
      v-if="fieldsEditor.active"
      :disabled="!fieldsEditor.valid"
      approve-text="Save"
      @confirm="saveFieldsEditor"
      @close="closeFieldsEditor"
    >
      <XCustomFields
        slot="body"
        v-model="fieldsEditor.data"
        :module="module"
        :fields="customFields"
        :external-error="error"
        @validate="validateFieldsEditor"
      />
    </XModal>
    <XToast
      v-if="toastMessage"
      v-model="toastMessage"
    />
  </div>
</template>

<script>
import { JSONView } from 'vue-json-component';
import {
  mapState, mapActions, mapGetters,
} from 'vuex';
import _get from 'lodash/get';
import _sortBy from 'lodash/sortBy';
import _isPlainObject from 'lodash/isPlainObject';
import _isArray from 'lodash/isArray';
import entityCustomData from '@mixins/entity_custom_data';
import XTabs from '../../../axons/tabs/Tabs.vue';
import XTab from '../../../axons/tabs/Tab.vue';
import XList from '../../../neurons/schema/List.vue';
import XModal from '../../../axons/popover/Modal/index.vue';
import XCustomFields from './CustomFields.vue';
import XToast from '../../../axons/popover/Toast.vue';

import { FETCH_DATA_FIELDS } from '../../../../store/actions';

import { pluginMeta } from '../../../../constants/plugin_meta';
import { guiPluginName, initCustomData, getEntityPermissionCategory } from '../../../../constants/entities';
import { GET_CONNECTION_LABEL } from '../../../../store/getters';


export default {
  name: 'XEntityAdapters',
  components: {
    XTabs,
    XTab,
    XList,
    XModal,
    XCustomFields,
    XToast,
    JsonView: JSONView,
  },
  mixins: [entityCustomData],
  props: {
    entityId: {
      type: String,
      required: true,
    },
    module: {
      type: String,
      required: true,
    },
    adapters: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      viewBasic: true,
      fieldsEditor: { active: false },
      toastMessage: '',
      error: {},
    };
  },
  computed: {
    ...mapState({
      fields(state) {
        return state[this.module].fields.data;
      },
      hyperlinks(state) {
        return state[this.module].hyperlinks.data;
      },
    }),
    ...mapGetters({
      getConnectionLabel: GET_CONNECTION_LABEL,
    }),
    userCannotEditDevices() {
      return this.$cannot(getEntityPermissionCategory(this.module),
        this.$permissionConsts.actions.Update);
    },
    sortedSpecificData() {
      const lastSeen = new Set();
      let res = this.adapters.filter((item) => {
        if (item.hidden_for_gui) return false;
        return !(item.plugin_type && item.plugin_type.toLowerCase().includes('plugin'));
      });
      res = res.map((item) => {
        item.id = `${item.plugin_unique_name}_${item.data.id}`;
        let connectionLabel = this.getConnectionLabel(item.client_used, {
          plugin_unique_name: item.plugin_unique_name,
        });
        item.connectionLabel = connectionLabel || item.client_used;
        if (connectionLabel !== '') {
          connectionLabel = ` - ${connectionLabel}`;
        }
        if (pluginMeta[item.plugin_name]) {
          item.pretty_name = pluginMeta[item.plugin_name].title + connectionLabel;
        }
        if (lastSeen.has(item.plugin_name)) return { ...item, outdated: true };
        lastSeen.add(item.plugin_name);
        return item;
      });
      const guiTitle = pluginMeta[initCustomData(this.module).plugin_name].title;
      res = _sortBy(res, (item) => {
        if (item.pretty_name === guiTitle) return null;
        return item.pretty_name;
      });
      if (res.length === 0 || res[res.length - 1].plugin_name !== guiPluginName) {
        // Add initial gui adapters data
        res.push({
          ...initCustomData(this.module),
          pretty_name: guiTitle,
        });
      }
      return res;
    },
    genericFieldNames() {
      return this.fields.generic.map((field) => field.name);
    },
    genericSchema() {
      const schema = _get(this.fields, 'schema.generic');
      if (!schema) return null;
      return {
        ...schema,
        name: 'data',
        title: 'SEPARATOR',
        hyperlinks: eval(this.hyperlinks.aggregator),
      };
    },
    genericSchemaNoId() {
      return {
        ...this.genericSchema,
        items: this.genericSchema.items.filter((item) => item.name !== 'id' && item.name !== 'specific_data.data.id'),
      };
    },
    customData() {
      return this.sortedSpecificData[this.sortedSpecificData.length - 1].data;
    },
    fieldTitles() {
      const createFieldsMap = (result, item) => ({ ...result, [this.trimName(item.name)]: item.title });
      return {
        predefined: this.customFields.predefined.reduce(createFieldsMap, {}),
        custom: this.customFields.custom.reduce(createFieldsMap, {}),
      };
    },
  },
  methods: {
    ...mapActions({
      fetchDataFields: FETCH_DATA_FIELDS,
    }),
    isGuiAdapterData(data) {
      return data.plugin_name === guiPluginName;
    },
    adapterSchema(name) {
      if (!this.fields || !this.fields.schema) return {};
      return {
        type: 'array',
        items: [(name === guiPluginName) ? this.genericSchemaNoId : this.genericSchema, {
          type: 'array',
          ...this.fields.schema.specific[name],
          name: 'data',
          title: 'SEPARATOR',
          hyperlinks: eval(this.hyperlinks[name]),
        }],
      };
    },
    toggleView() {
      this.viewBasic = !this.viewBasic;
    },
    editFields() {
      this.fieldsEditor = {
        active: true,
        data: this.prepareCustomData(this.customData),
        valid: true,
      };
    },
    saveFieldsEditor() {
      if (!this.fieldsEditor.valid) return;
      this.saveEntityCustomData({
        ids: [this.entityId],
        include: true,
      }, this.fieldsEditor.data).then(() => {
        this.toastMessage = 'Saved Custom Data';
        this.fetchDataFields({
          module: this.module,
        });
        this.closeFieldsEditor();
      }).catch((error) => {
        this.error = error.response.data.message;
      });
    },
    closeFieldsEditor() {
      this.fieldsEditor = { active: false };
      this.error = {};
    },
    validateFieldsEditor(valid) {
      this.fieldsEditor.valid = valid;
    },
    prepareCustomData(customData) {
      return Object.entries(customData)
        .reduce((items, [name, value]) => {
          const res = this.customUserField(name)
            ? [{
              name, value, title: this.fieldTitles.custom[name], predefined: false,
            }]
            : this.flattenCustomData(`specific_data.data.${name}`, value);
          return [...items, ...res];
        }, []);
    },
    flattenCustomData(name, value, result = []) {
      /**
       * Recursive function that flats a server side object into a dot seperated path.
       * for example {os: {type: 'windows'}} => 'specific_data.data.os.type'
       */
      if (_isPlainObject(value)) {
        return Object.entries(value).reduce((accumulatorResult, [key, val]) => (
          this.flattenCustomData(`${name}.${key}`, val, accumulatorResult)), result);
      } if (_isArray(value)) {
        return value.reduce((accumulatorResult, items) => (
          Object.entries(items).reduce((nestedAccumulatorResult, [key, val]) => (
            this.flattenCustomData(`${name}.${key}`, val, nestedAccumulatorResult)), accumulatorResult)), result);
      }
      return result.concat({ name, value, predefined: true });
    },
  },
};
</script>

<style lang="scss">
  .x-entity-adapters {
    height: 100%;

    .x-tabs .body .header {
      padding-bottom: 4px;
      margin-bottom: 12px;
      border-bottom: 2px solid #1d222cb3;
      display: flex;
      align-items: center;
      overflow: hidden;

      &__source {
        flex: 1 0 auto;
        width: calc(100% - 120px);
        text-overflow: ellipsis;
        overflow: hidden;
        .data_from {
          font-size: 16px;
          font-weight: bolder;
        }
      }
    }
    .json-view-item {
      .data-key {
        padding: 2px;
      }
      .chevron-arrow {
        border-right-width: 2px;
        border-bottom-width: 2px;
      }
    }
  }
</style>
