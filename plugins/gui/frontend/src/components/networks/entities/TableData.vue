<template>
  <div>
    <div
      class="x-data"
      @mouseover="onHoverData"
      @mouseleave="onLeaveData"
    >
      <div class="data-table-container">
        <APopover
          placement="rightTop"
          :visible="hoverData"
          :get-popup-container="getPopupContainerAdapter"
          :destroy-tooltip-on-hide="true"
        >
          <template slot="content">
            <XTable
              slot="body"
              v-bind="adaptersDetailsTable"
            />
          </template>
          <XTableData
            :schema="schema"
            :data="data"
            :sort="sort"
            :filter="filter"
          />

        </APopover>
      </div>

      <div class="details-table-container">
        <APopover
          placement="bottom"
          :visible="expandData"
          :get-popup-container="getPopupContainer"
          :destroy-tooltip-on-hide="true"
        >
          <template slot="content">
            <div
              class="content"
            >
              <XTable v-bind="detailsTable">
                <template #default="slotProps">
                  <XTableData
                    v-bind="slotProps"
                    :module="module"
                  />
                </template>
              </XTable>
            </div>
          </template>
          <XIcon
            v-if="showExpand"
            :class="{active: expandData}"
            :style="{padding: '0 4px'}"
            :type="expandData ? 'left-circle' : 'right-circle'"
            @click.native.stop="toggleCell"
          />
        </APopover>
      </div>
    </div>
    <div
      v-if="expandRow"
      class="details-list-container"
    >
      <div class="list">
        <XTableData
          v-for="(detail, index) in details"
          :key="index"
          :schema="schema"
          :data="detail"
          :sort="sort"
          :filter="filter"
          class="item"
        />
      </div>
    </div>
  </div>
</template>

<script>
import _isEmpty from 'lodash/isEmpty';
import _orderBy from 'lodash/orderBy';
import _map from 'lodash/map';
import _extend from 'lodash/extend';
import { mapState, mapGetters } from 'vuex';
import { pluginMeta } from '@constants/plugin_meta';
import { GET_CONNECTION_LABEL } from '@store/getters';
import XIcon from '@axons/icons/Icon';
import XTable from '@axons/tables/Table.vue';
import XTableData from '@neurons/data/TableData';
import { Popover } from 'ant-design-vue';

export default {
  name: 'XEntityTableData',
  components: {
    XTable,
    XTableData,
    XIcon,
    APopover: Popover,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    schema: {
      type: Object,
      required: true,
    },
    data: {
      type: Object,
      required: true,
    },
    sort: {
      type: Object,
      default: () => ({
        field: '', desc: true,
      }),
    },
    filter: {
      type: Array,
      default: () => [],
    },
    hoverRow: {
      type: Boolean,
      default: false,
    },
    expandRow: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      hoverData: false,
      expandData: false,
      position: {
        top: false,
        left: false,
      },
    };
  },
  computed: {
    ...mapState({
      adaptersSchema(state) {
        return state[this.module].fields.data.generic[0];
      },
      colExcludedAdapters(state) {
        return state[this.module].view.colExcludedAdapters[this.fieldName];
      },
    }),
    ...mapGetters({
      getConnectionLabel: GET_CONNECTION_LABEL,
    }),
    fieldName() {
      return this.schema.name;
    },
    adaptersFieldName() {
      return this.adaptersSchema.name;
    },
    isAdaptersField() {
      return this.fieldName === this.adaptersFieldName;
    },
    getAdapters() {
      let adapters = this.data[this.adaptersFieldName];
      if (this.colExcludedAdapters) {
        adapters = adapters.filter((adapter) => !this.colExcludedAdapters.includes(adapter));
      }
      return adapters;
    },
    adaptersLength() {
      return this.getAdapters.length;
    },
    showExpand() {
      return (this.hoverRow || this.expandData) && this.adaptersLength > 1 && this.fieldName.includes('specific_data')
      && !this.fieldName.includes('_preferred') && !_isEmpty(this.data[this.fieldName]);
    },
    adaptersList() {
      return this.getAdapters.concat().map((adapter) => [adapter]).sort();
    },
    adaptersDetailsWithClientIdList() {
      return this.getAdapters.concat().map((adapter, index) => ({
        pluginName: [adapter],
        clientId: this.data['meta_data.client_used'][index],
      })).sort((a, b) => ((a.pluginName[0] > b.pluginName[0]) ? 1 : -1));
    },
    adaptersDetailsData() {
      return _orderBy(this.adaptersDetailsWithClientIdList.map((adapter) => {
        const connectionLabel = this.getConnectionLabel(adapter.clientId, {
          plugin_name: adapter.pluginName[0],
        });
        let name = pluginMeta[adapter.pluginName[0]]
          ? pluginMeta[adapter.pluginName[0]].title
          : adapter.pluginName[0];
        if (connectionLabel !== '') {
          name = `${name} - ${connectionLabel}`;
        }
        return {
          [this.fieldName]: adapter.pluginName,
          name,
        };
      }), [this.fieldName]);
    },
    details() {
      if (this.isAdaptersField) {
        // pass list of adapters with title and logo flag
        return _map(this.adaptersDetailsData, (item) => _extend({}, item, { formatTitle: () => `${item.name}` }));
      }
      // auto generated fields that are not saved in the db (Like _preferred fields) dont have _details
      if (this.data[`${this.fieldName}_details`] !== undefined) {
        return this.data[`${this.fieldName}_details`];
      }
      // If you just want the aggregated value to be on top when expanding, return a list with '' the size of adapters list
      return this.data.adapter_list_length_details;
    },
    detailsTable() {
      const baseTable = {
        fields: [
          this.adaptersSchema,
          this.schema,
        ],
        data: this.details.map((detail, i) => ({
          [this.adaptersFieldName]: this.adaptersList[i],
          [this.fieldName]: detail,
          formatTitle: () => `${this.adaptersDetailsData[i].name}`,
        })),
        colFilters: {
          [this.schema.name]: this.filter,
        },
        filterable: false,
      };
      if (this.schema.type === 'string' && this.schema.format === 'date-time') {
        baseTable.fields.push({
          name: 'days', title: 'Days', type: 'integer',
        });
        baseTable.data = baseTable.data.map((item) => {
          if (!item[this.schema.name]) return item;
          const nowDate = new Date();
          nowDate.setHours(0, 0, 0, 0);
          const itemDate = new Date(item[this.schema.name]);
          itemDate.setHours(0, 0, 0, 0);
          return {
            ...item,
            days: Math.ceil((nowDate.getTime() - itemDate.getTime()) / 60 / 60 / 24 / 1000),
          };
        }).sort((a, b) => {
          if (_isEmpty(a[this.schema.name])) return 1;
          if (_isEmpty(b[this.schema.name])) return -1;
          return (new Date(b[this.schema.name]) - new Date(a[this.schema.name]));
        });
      }
      return baseTable;
    },
    adaptersDetailsTable() {
      return {
        fields: [
          this.schema, {
            name: 'name', title: 'Name', type: 'string',
          }],
        data: this.adaptersDetailsData,
        colFilters: {
          [this.schema.name]: this.filter,
        },
        filterable: false,
      };
    },
  },
  methods: {
    toggleCell() {
      this.expandData = !this.expandData;
    },
    onHoverData() {
      if (!this.isAdaptersField) {
        return;
      }
      this.hoverData = true;
    },
    onLeaveData() {
      this.hoverData = false;
    },
    getPopupContainer() {
      return this.$el.closest('.table');
    },
    getPopupContainerAdapter() {
      return this.$el.querySelector('.x-data');
    },
  },
};
</script>

<style lang="scss">
  .x-data {
    display: flex;
    position: relative;

    .details-table-container {
      min-width: 24px;

      .x-icon:hover {
        color: $theme-orange;
      }
    }

    .data-table-container {
      position: relative;
    }
  }

  .details-list-container {
    overflow: visible;
    margin: 0px -8px;
    animation: vertical-fade .6s ease-in-out;

    @keyframes vertical-fade {
      from {
        opacity: 0;
        transform: translateY(-50%);
      }
    }

    .list {
      margin-top: 2px;
      padding-left: 8px;
      display: grid;
      grid-gap: 2px 0;
      background-color: rgba($grey-2, 0.6);

      > .item {
        height: 30px;
        display: flex;
        align-items: center;
        border-bottom: 2px solid $theme-white;
        padding: 4px 8px;

        &:last-child {
          border: none;
        }
      }
    }
  }
</style>
