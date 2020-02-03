<template>
  <div class="x-compliance-table">
    <x-table-wrapper
      title="Rules"
      :count="data.length"
      :loading="loading"
      :error="error"
    >
      <template slot="actions">
        <x-button
          link
          @click="exportCSV"
        >Export CSV</x-button>
      </template>
      <x-table
        slot="table"
        v-model="selectedRules"
        :fields="filteredFields"
        module="compliance"
        :data="data"
        :row-class="getRowClass"
        :pagination="false"
        :on-click-row="openSidePanel"
        :static-sort="false"
        :format-title="formatTitle"
        :multiple-row-selection="false"
        id-field="section"
      />
    </x-table-wrapper>
    <x-compliance-panel
      :data="currentRule"
      :fields="fields"
      @close="closeSidePanel"
    />
  </div>
</template>
<script>
import { mapActions, mapState } from 'vuex';
import { FETCH_DATA_CONTENT_CSV } from '@store/actions';
import xTable from '@components/axons/tables/Table.vue';
import xTableWrapper from '@axons/tables/TableWrapper.vue';
import xButton from '@axons/inputs/Button.vue';
import xCompliancePanel from './CompliancePanel';

export default {
  name: 'XComplianceTable',
  components: {
    xCompliancePanel,
    xTable,
    xTableWrapper,
    xButton,
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
  },
  data() {
    return {
      currentRule: null,
      exporting: null,
    };
  },
  mounted() {
    const { section } = this.$route.params;
    if (section) {
      this.currentRule = this.complianceRulesBySection[section];
    }
  },
  computed: {
    ...mapState({
      fields(state) {
        return state[this.module].view.schema_fields;
      },
    }),
    selectedRules() {
      return this.currentRule ? [this.currentRule.section] : [];
    },
    complianceRulesBySection() {
      return this.data.reduce((map, rule) => {
        map[rule.section] = rule;
        return map;
      }, {});
    },
    filteredFields() {
      return this.fields.filter((field) => field.expanded === undefined);
    },
  },
  methods: {
    ...mapActions({
      fetchContentCSV: FETCH_DATA_CONTENT_CSV,
    }),
    getRowClass(rowData) {
      return rowData.status.toLowerCase().replace(' ', '-');
    },
    openSidePanel(section) {
      this.currentRule = this.complianceRulesBySection[section];
      this.$router.push({ path: encodeURI(`/cloud_compliance/${section}`) });
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
  $header-height: 60px;

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
      width: 700px;
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
        background-color: transparent!important;
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
