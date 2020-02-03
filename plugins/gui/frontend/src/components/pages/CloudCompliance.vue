<template>
  <x-page
    class="x-cloud-compliance"
    title="Cloud Asset Compliance Center"
    :beta="true"
  >
    <div class="cis-header">
      <div class="subtitle">
        CIS Amazon Web Services Foundations Benchmark V1.2
      </div>
      <div class="accounts-filter">
        <x-combobox
          v-if="accounts.length"
          v-model="filterAccounts"
          height="30"
          :selection-display-limit="1"
          :items="accounts"
          label="Accounts"
          multiple
          :allow-create-new="false"
          :hide-quick-selections="false"
          :menu-props="{maxWidth: 300}"
          @change="applySearchAndFilter"
        />
      </div>
      <x-button
        class="search__reset"
        link
        @click="resetAccountsFilter"
      >Reset</x-button>
      <md-switch
        v-model="failedOnly"
        class="failed-only"
      >Failed rules only</md-switch>
    </div>
    <x-compliance-table
      v-if="allCloudComplianceRules"
      module="compliance"
      :cis-name="cisName"
      :data="filteredData"
      :loading="loading"
      :error="error"
    />
    <x-compliance-tip
      v-if="!enabled"
    />
  </x-page>
</template>
<script>
import _filter from 'lodash/filter';
import _debounce from 'lodash/debounce';
import _get from 'lodash/get';
import { mapState, mapGetters } from 'vuex';
import xPage from '@axons/layout/Page.vue';
import xButton from '@axons/inputs/Button.vue';
import xCombobox from '@axons/inputs/combobox/index.vue';
import xComplianceTable from '@components/networks/compliance/ComplianceTable.vue';
import xComplianceTip from '@components/networks/compliance/ComplianceTip.vue';
import { fetchCompliance, fetchComplianceAccounts } from '@api/compliance';
import { IN_TRIAL } from '@store/modules/settings';

export default {
  name: 'XCloudCompliance',
  components: {
    xPage,
    xComplianceTable,
    xComplianceTip,
    xButton,
    xCombobox,
  },
  data() {
    return {
      cisName: 'cis_aws',
      allCloudComplianceRules: null,
      accounts: [],
      filterAccounts: [],
      failedOnly: false,
      loading: false,
      error: null,
    };
  },
  computed: {
    ...mapGetters({
      inTrial: IN_TRIAL,
    }),
    ...mapState({
      featureFlags(state) {
        if (!state.settings.configurable.gui || !state.settings.configurable.gui.FeatureFlags) {
          return null;
        }
        return state.settings.configurable.gui.FeatureFlags.config;
      },
    }),
    name() {
      return 'compliance';
    },
    filteredData() {
      if (this.failedOnly) {
        return _filter(this.allCloudComplianceRules,
          (rule) => rule.status === 'Failed');
      }
      return this.allCloudComplianceRules;
    },
    enabled() {
      return this.inTrial
        || (_get(this.featureFlags, 'cloud_compliance.cis_enabled'));
    },
  },
  async created() {
    this.loading = true;
    await this.fetchComplianceAccounts();
    await this.fetchComplianceRows();
    this.loading = false;
  },
  methods: {
    async fetchComplianceRows() {
      try {
        this.allCloudComplianceRules = await fetchCompliance(this.cisName, this.filterAccounts);
      } catch (ex) {
        this.error = 'Internal Server Error';
        this.loading = false;
      }
    },
    async fetchComplianceAccounts() {
      try {
        this.accounts = await fetchComplianceAccounts(this.cisName);
      } catch (ex) {
        this.error = 'Internal Server Error';
        this.loading = false;
      }
    },
    resetAccountsFilter() {
      this.filterAccounts = [];
      this.updateCurrentView();
    },
    applySearchAndFilter: _debounce(function applySearchAndFilter() {
      this.updateCurrentView();
    }, 250),
    async updateCurrentView() {
      this.loading = true;
      await this.fetchComplianceRows();
      this.loading = false;
    },
  },
};
</script>


<style lang="scss">
  .x-cloud-compliance {
    .cis-header {
      display: flex;
      align-items: flex-end;
      line-height: 28px;
      margin-right: 16px;

      .subtitle {
        font-size: 16px;
        font-weight: 400;
        color: $theme-black;
        margin-top: 12px;
        margin-right: 24px;
      }
      .accounts-filter {
        width: 300px;
        margin-left: 40px;
        .x-combobox {
          font-size: 14px;

          .v-input__control {
            border: 1px solid #DEDEDE !important;
          }
        }
      }
      .search__reset {
        width: 100px;
      }
      .failed-only {
        margin-bottom: 4px;
      }
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
        background-color: $grey-3;
      }
    }
  }
</style>
