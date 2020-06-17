<template>
  <div class="x-compliance-table">
    <XTable
      slot="table"
      v-model="selectedRules"
      :show-table-spinner="loading"
      title="Rules"
      :module="modulePath"
      :static-data="data"
      :row-class="getRowClass"
      :pagination="true"
      :on-click-row="openSidePanel"
      :fields="getTableFields()"
      :static-sort="false"
      :format-title="formatTitle"
      :multiple-row-selection="false"
      id-field="id"
    >
      <template slot="actions">
        <XEnforcementMenu
          :cis-name="cisName"
          :cis-title="cisTitle"
          :accounts="accounts"
          :module="module"
          :disabled="false"
          :rules="rules"
          :categories="categories"
          :failed-only="failedOnly"
          :aggregated-view="aggregatedView"
        />
        <XButton
          type="link"
          class="compliance-action-button export-csv"
          :loading="exporting"
          @click.stop.prevent="exportCSV"
        >
          <VIcon
            size="18"
          >$vuetify.icons.entityExport</VIcon>
          <span class="export-csv-title">Export CSV</span>
        </XButton>
      </template>
    </XTable>
    <XCompliancePanel
      :data="currentRule"
      :fields="fields"
      :date-format="dateFormat"
      @close="closeSidePanel"
    />
  </div>
</template>
<script>
import { mapActions, mapState, mapGetters } from 'vuex';
import PulseLoader from 'vue-spinner/src/PulseLoader.vue';

import { FETCH_DATA_CONTENT_CSV } from '@store/actions';
import XTable from '@components/neurons/data/Table.vue';
import XButton from '@axons/inputs/Button.vue';
import { DATE_FORMAT } from '../../../store/getters';
import XCompliancePanel from './CompliancePanel';
import XEnforcementMenu from './ComplianceEnforceMenu.vue';


const tableFields = [{
  name: 'status', title: '', type: 'string', format: 'status',
}, {
  name: 'section', title: 'Section', type: 'string',
}, {
  name: 'rule', title: 'Rule', type: 'string',
}, {
  name: 'category', title: 'Category', type: 'string',
}, {
  name: 'account', title: 'Account', type: 'array', items: { type: 'string' }, limit: 1,
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
    XCompliancePanel,
    XTable,
    XButton,
    PulseLoader,
    XEnforcementMenu,
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
    cisTitle: {
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
    rules: {
      type: Array,
      default: () => [],
    },
    categories: {
      type: Array,
      default: () => [],
    },
    failedOnly: {
      type: Boolean,
      default: false,
    },
    aggregatedView: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      currentRuleId: null,
      exporting: null,
    };
  },
  computed: {
    ...mapState({
      fields(state) {
        return state[this.module].view.schema_fields;
      },
    }),
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    selectedRules() {
      return this.currentRule ? { ids: [this.currentRuleId], include: true }
        : { ids: [], include: true };
    },
    complianceRulesById() {
      return this.data.reduce((map, rule) => {
        // eslint-disable-next-line no-param-reassign
        map[rule.id] = rule;
        return map;
      }, {});
    },
    currentRule() {
      if (this.currentRuleId) {
        return this.complianceRulesById[this.currentRuleId];
      }
      return null;
    },
    modulePath() {
      return `${this.module}/cis/${this.cisName}/report`;
    },
  },
  watch: {
    $route(to) {
      this.currentRuleId = to.params.id;
    },
  },
  mounted() {
    const { id } = this.$route.params;
    if (id) {
      this.currentRuleId = id;
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
      this.currentRuleId = id;
      this.$router.push({ path: encodeURI(`/cloud_asset_compliance/${id}`) });
    },
    closeSidePanel() {
      this.currentRuleId = null;
      this.$router.push({ path: '/cloud_asset_compliance' });
    },
    exportCSV() {
      this.fetchContentCSV({
        module: this.module,
        endpoint: `${this.module}/${this.cisName}`,
        source: 'cloud',
        accounts: this.accounts,
        rules: this.rules,
        categories: this.categories,
        failedOnly: this.failedOnly,
        aggregatedView: this.aggregatedView,
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
  $header-height: 90px;

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
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
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
      width: 250px;
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

  .ant-btn.x-button {
    &.compliance-action-button.export-csv {
      padding-right: 0px;
    }
    &.compliance-action-button:not([disabled]) {
      width: auto;
      color: $theme-black;
      svg {
        stroke: $theme-black;
      }
      &.menuOpened {
        color: $theme-blue;
        svg {
          stroke: $theme-blue;
        }
      }
      &.action {
        width: auto;
      }
    }
    &.compliance-action-button:not([disabled]):hover {
      color: $theme-blue;
      svg {
        stroke: $theme-blue;
        .stroke-color {
          stroke: $theme-blue;
        }
        .fill-color {
          fill: $theme-blue;
        }
      }
    }
    .export-csv-title {
      margin-left: 3px;
    }
  }
</style>
