<template>
  <div class="x-compliance-table">
    <div
      v-if="loading"
      class="v-spinner-bg"
    />
    <pulse-loader
      :loading="loading"
      color="#FF7D46"
    />
    <x-table
      slot="table"
      v-model="selectedRules"
      title="Rules"
      module="compliance/cis_aws/report"
      :static-data="data"
      :row-class="getRowClass"
      :pagination="true"
      page-size="42"
      :page-sizes="[42, 84]"
      :on-click-row="openSidePanel"
      :static-fields="getTableFields()"
      :static-sort="false"
      :format-title="formatTitle"
      :multiple-row-selection="false"
      id-field="id"
    >
      <template slot="actions">
        <x-button
          link
          @click="exportCSV"
        >Export CSV
        </x-button>
      </template>
    </x-table>
    <x-compliance-panel
      :data="currentRule"
      :fields="fields"
      @close="closeSidePanel"
    />
  </div>
</template>
<script>
import { mapActions, mapState } from 'vuex';
import PulseLoader from 'vue-spinner/src/PulseLoader.vue';

import { FETCH_DATA_CONTENT_CSV } from '@store/actions';
import xTable from '@components/neurons/data/Table.vue';
import xButton from '@axons/inputs/Button.vue';
import xCompliancePanel from './CompliancePanel';

const tableFields = [{
  name: 'status', title: '', type: 'string', format: 'status',
}, {
  name: 'section', title: 'Section', type: 'string',
}, {
  name: 'rule', title: 'Rule', type: 'string',
}, {
  name: 'category', title: 'Category', type: 'string',
}, {
  name: 'account', title: 'Account', type: 'string',
}, {
  name: 'results', title: 'Results (Failed/Checked)', type: 'string',
}, {
  name: 'affected', title: 'Affected Devices/Users', type: 'integer',
}, {
  name: 'last_updated', title: 'Last Updated', type: 'string', format: 'date-time',
}];

export default {
  name: 'XComplianceTable',
  components: {
    xCompliancePanel,
    xTable,
    xButton,
    PulseLoader,
  },
  props: {
    module: {
      type: String,
      default: '',
    },
    cisName: {
      type: String,
      default: '',
    },
    data: {
      type: Array,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: null,
    },
    accounts: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      currentRule: null,
      exporting: null,
    };
  },
  computed: {
    ...mapState({
      fields(state) {
        return state[this.module].view.schema_fields;
      },
    }),
    selectedRules() {
      return this.currentRule ? { ids: [this.currentRule.section], include: true }
        : { ids: [], include: true };
    },
    complianceRulesById() {
      return this.data.reduce((map, rule) => {
        // eslint-disable-next-line no-param-reassign
        map[rule.id] = rule;
        return map;
      }, {});
    },
  },
  mounted() {
    const { id } = this.$route.params;
    if (id) {
      this.currentRule = this.complianceRulesById[id];
    }
  },
  methods: {
    ...mapActions({
      fetchContentCSV: FETCH_DATA_CONTENT_CSV,
    }),
    getTableFields() {
      return tableFields;
    },
    getRowClass(rowData) {
      return rowData.status.toLowerCase().replace(' ', '-');
    },
    openSidePanel(id) {
      this.currentRule = this.complianceRulesById[id];
      this.$router.push({ path: encodeURI(`/cloud_compliance/${id}`) });
    },
    closeSidePanel() {
      this.currentRule = null;
      this.$router.push({ path: '/cloud_compliance' });
    },
    exportCSV() {
      this.fetchContentCSV({
        module: this.module,
        endpoint: `${this.module}/${this.cisName}`,
        source: 'cloud',
        accounts: this.accounts,
      }).then(() => {
        this.exporting = false;
      });
      this.exporting = true;
    },
    formatTitle(rule, field) {
      if (field === 'status' && rule.status === 'No Data') {
        return rule.error;
      }
      return rule[field];
    },
  },
};
</script>
<style lang="scss">
  $header-height: 20px;

  .x-compliance-table {
    height: calc(100% - #{$header-height});

    .x-table-head {
      min-width: 20px;
    }

    .header {
      display: flex;
      line-height: 28px;
      margin-right: 16px;

      .subtitle {
        font-size: 16px;
        font-weight: 400;
        color: $theme-black;
        margin-top: 12px;
        margin-right: 24px;
      }
    }

    .table-td-status {
      width: 20px;
    }

    .table-td-section {
      width: 40px;
    }

    .table-td-rule {
      width: 500px;
      text-overflow: ellipsis;
      overflow: hidden;
    }

    .table-td-category {
      width: 300px;
    }

    .table-td-account {
      width: 400px;
    }

    .failed {
      .table-td-results {
        color: $indicator-error;
      }

      .table-td-affected {
        color: $indicator-error;
      }
    }

    .status {
      width: 10px;
      height: 10px;
      border-radius: 10px;

      &.passed {
        background-color: $indicator-success;
      }

      &.failed {
        background-color: $indicator-error;
      }

      &.no-data {
        background-color: transparent !important;
        width: 0;
        height: 0;
        border-left: 6px solid transparent;
        border-right: 6px solid transparent;
        border-bottom: 10px solid $indicator-warning;
        border-radius: unset;
      }
    }
  }
</style>
