<template>
  <XPage
    class="x-cloud-compliance-page"
    title="Cloud Asset Compliance Center"
  >
    <div class="x-cloud-compliance">
      <div class="cis-header">

        <div class="cis-row cis-type">
          <div class="subtitle">
            Compliance :
          </div>
          <XComplianceSelect
            :value="cisName"
            :options="complianceOptions"
            type="img"
            class="cis-select"
            @input="complianceSelected"
          />
        </div>

        <div class="cis-row cis-filter">
          <div class="filter-item accounts-filter table-filter">
            <XCombobox
              v-if="accounts"
              v-model="filteredAccounts"
              height="30"
              :selection-display-limit="1"
              :items="accounts"
              label="Accounts"
              multiple
              :allow-create-new="false"
              :hide-quick-selections="false"
              :menu-props="{maxWidth: 230}"
              @change="fetchAllData"
            />
          </div>
          <div class="filter-item rules-filter table-filter">
            <XCombobox
              v-if="rules"
              v-model="filteredRules"
              height="30"
              :selection-display-limit="1"
              :items="rulesFilterOptions"
              label="Rule"
              multiple
              :allow-create-new="false"
              :hide-quick-selections="false"
              :menu-props="{maxWidth: 230}"
              :custom-sort="rulesSort"
              @change="fetchAllData"
            />
          </div>
          <div class="filter-item categories-filter table-filter">
            <XCombobox
              v-if="categories"
              v-model="filteredCategories"
              height="30"
              :selection-display-limit="1"
              :items="categories"
              label="Category"
              multiple
              :allow-create-new="false"
              :hide-quick-selections="false"
              :menu-props="{maxWidth: 230}"
              @change="fetchAllData"
            />
          </div>
          <XSwitch
            :checked="failedOnly"
            class="failed-only"
            label="Failed only"
            @change="toggleFailedSwitch"
          />
          <XSwitch
              :checked="aggregatedView"
              class="cross-account"
              label="Aggregated view"
              @change="toggleCrossAccountsSwitch"
          />
          <XButton
            class="search__reset"
            type="link"
            @click="resetAccountsFilter"
          >Reset</XButton>
        </div>
        <div class="cis-score">
          <XComplianceScore
            v-model="selectedActiveRules"
            :score="getCurrentScore"
            :all-cis-rules="rulesLabels"
            :custom-sort="rulesSort"
            :cis-title="cisTitle"
            @save-rules="updateActiveRules"
            :lock-compliance-actions="complianceDisabled || complianceExpired"
          />
        </div>
      </div>
      <XComplianceTable
        :module="module"
        :cis-name="cisName"
        :cis-title="cisTitle"
        :data="allCloudComplianceRules"
        :loading="loading"
        :error="error"
        :accounts="accountsToHandle"
        :rules="filteredRules"
        :categories="filteredCategories"
        :failed-only="failedOnly"
        :aggregated-view="aggregatedView"
        :lock-compliance-actions="complianceDisabled || complianceExpired"
      />
    </div>
    <XComplianceTip
      v-if="complianceDisabled"
    />
    <XComplianceExpireModal
      v-if="complianceExpired"
    />
  </XPage>
</template>
<script>
import _get from 'lodash/get';
import _isEmpty from 'lodash/isEmpty';
import { mapState, mapGetters, mapMutations } from 'vuex';

import { UPDATE_COMPLIANCE_FILTERS } from '@store/modules/compliance';

import XPage from '@axons/layout/Page.vue';
import XButton from '@axons/inputs/Button.vue';
import XCombobox from '@axons/inputs/combobox/index.vue';
import XSwitch from '@axons/inputs/Switch.vue';
import XComplianceTable from '@components/networks/compliance/ComplianceTable.vue';
import XComplianceTip from '@components/networks/compliance/ComplianceTip.vue';
import XComplianceExpireModal from '@components/networks/compliance/ComplianceExpireModal.vue';
import XComplianceScore from '@components/networks/compliance/ComplianceScore.vue';
import {
  fetchCompliance, fetchComplianceInitialCis, fetchComplianceReportFilters, updateComplianceRules,
} from '@api/compliance';
import { IN_TRIAL, IS_CLOUD_COMPLIANCE_EXPIRED } from '@store/modules/settings';
import XComplianceSelect from '../networks/compliance/ComplianceSelect.vue';

export default {
  name: 'XCloudCompliance',
  components: {
    XPage,
    XComplianceTable,
    XComplianceTip,
    XButton,
    XCombobox,
    XComplianceScore,
    XComplianceSelect,
    XSwitch,
    XComplianceExpireModal,
  },
  data() {
    return {
      module: 'compliance',
      cisName: 'aws',
      allCloudComplianceRules: [],
      accounts: [],
      rules: [],
      loading: true,
      error: null,
      complianceOptions: [
        { name: 'aws', title: 'CIS Amazon Web Services Foundations Benchmark V1.2' },
        /* { name: 'azure', title: 'CIS Microsoft Azure Foundations Benchmark V1.1' }, */
      ],
      score: 0,
      activeRules: [],
    };
  },
  computed: {
    ...mapGetters({
      inTrial: IN_TRIAL,
      isExpired: IS_CLOUD_COMPLIANCE_EXPIRED,
    }),
    ...mapState({
      featureFlags(state) {
        if (!state.settings.configurable.gui || !state.settings.configurable.gui.FeatureFlags) {
          return null;
        }
        return state.settings.configurable.gui.FeatureFlags.config;
      },
      filters(state) {
        return state[this.module].cis[this.cisName].report.view.filters;
      },
    }),
    name() {
      return 'compliance';
    },
    enabled() {
      const cisEnabled = _get(this.featureFlags, 'cloud_compliance.cis_enabled');
      return this.inTrial || cisEnabled;
    },
    getCurrentScore() {
      return this.score;
    },
    cisTitle() {
      return this.complianceOptions.find((item) => item.name === this.cisName).title;
    },
    accountsToHandle() {
      if (_isEmpty(this.filters.accounts)) {
        return this.accounts;
      }
      return this.filters.accounts;
    },
    filteredAccounts: {
      get() {
        return this.filters.accounts;
      },
      set(value) {
        this.updateComplianceFilters(value, 'accounts');
      },
    },
    filteredRules: {
      get() {
        return this.filters.rules;
      },
      set(value) {
        this.updateComplianceFilters(value, 'rules');
      },
    },
    rulesFilterOptions() {
      return this.rules.filter((rule) => rule.include_in_score).map((rule) => this.prepareRuleOptionName(rule));
    },
    filteredCategories: {
      get() {
        return this.filters.categories;
      },
      set(value) {
        this.updateComplianceFilters(value, 'categories');
      },
    },
    selectedActiveRules: {
      get() {
        return this.activeRules;
      },
      set(value) {
        this.activeRules = value;
      },
    },
    failedOnly: {
      get() {
        return this.filters.failedOnly;
      },
      set(value) {
        this.updateComplianceFilters(value, 'failedOnly');
      },
    },
    aggregatedView: {
      get() {
        return this.filters.aggregatedView;
      },
      set(value) {
        this.updateComplianceFilters(value, 'aggregatedView');
      },
    },
    rulesLabels() {
      return this.rules.map((rule) => this.prepareRuleOptionName(rule));
    },
    categories() {
      const uniqueCategories = new Set();
      this.rules.forEach((rule) => {
        if (rule.include_in_score) {
          uniqueCategories.add(rule.category);
        }
      });
      return Array.from(uniqueCategories);
    },
    complianceDisabled() {
      return this.featureFlags && !this.enabled;
    },
    complianceExpired() {
      return this.featureFlags && this.enabled && this.isExpired;
    },
  },
  mounted() {
    this.fetchInitData();
  },
  methods: {
    ...mapMutations({ updateFilters: UPDATE_COMPLIANCE_FILTERS }),
    async fetchAllData() {
      this.loading = true;
      await this.fetchComplianceRows();
      this.loading = false;
    },
    async fetchComplianceFilters() {
      const filters = await fetchComplianceReportFilters(this.cisName);
      this.accounts = _get(filters, 'accounts', []);
      this.rules = _get(filters, 'rules', []);

      const filteredActiveRules = this.rules.filter((rule) => rule.include_in_score);
      this.activeRules = filteredActiveRules.map((rule) => this.prepareRuleOptionName(rule));
    },
    async fetchComplianceRows() {
      try {
        const data = await fetchCompliance(
          this.cisName,
          this.filteredAccounts,
          this.filteredRules,
          this.filteredCategories,
          this.failedOnly,
          this.aggregatedView,
        );
        this.allCloudComplianceRules = data.rules;
        this.score = data.score;
      } catch (ex) {
        this.error = 'Internal Server Error';
        this.loading = false;
      }
    },
    async fetchInitData() {
      try {
        const reportsInfo = await fetchComplianceInitialCis();
        this.cisName = _get(reportsInfo, 'cis', 'aws');
        await this.fetchComplianceFilters();
        await this.fetchAllData();
      } catch (ex) {
        this.error = 'Internal Server Error';
        this.loading = false;
      }
    },
    resetAccountsFilter() {
      this.filteredAccounts = [];
      this.filteredRules = [];
      this.filteredCategories = [];
      this.updateCurrentView();
      this.failedOnly = false;
    },
    async updateCurrentView() {
      this.loading = true;
      await this.fetchComplianceRows();
      this.loading = false;
    },
    complianceSelected(cis) {
      this.cisName = cis;
      this.accounts = [];
      this.fetchAllData();
    },
    isRuleFailed(status) {
      return status === 'Failed' || status === 'No Data';
    },
    toggleFailedSwitch() {
      this.failedOnly = !this.failedOnly;
      this.fetchAllData();
    },
    toggleCrossAccountsSwitch() {
      this.aggregatedView = !this.aggregatedView;
      this.fetchAllData();
    },
    async updateComplianceFilters(value, filterName) {
      this.updateFilters({
        cisName: this.cisName,
        filterName,
        value,
      });
    },
    rulesSort(item1, item2) {
      return item1.toLowerCase().localeCompare(item2.toLowerCase(), undefined, { numeric: true });
    },
    prepareActiveRulesMap() {
      // Instead of updating all rules in db, will update only relevant rules.
      const includeScoreMap = this.allCloudComplianceRules.reduce((acc, item) => {
        acc[item.rule] = false;
        return acc;
      }, {});
      this.activeRules.forEach((ruleTitle) => {
        const ruleName = ruleTitle.substr(ruleTitle.indexOf(' ') + 1); // get only rule name, without section.
        includeScoreMap[ruleName] = true;
      });
      return includeScoreMap;
    },
    async updateActiveRules() {
      await updateComplianceRules(this.cisName, this.prepareActiveRulesMap(), this.cisTitle);
      await this.fetchComplianceFilters();
      await this.updateCurrentView();
    },
    prepareRuleOptionName(rule) {
      return `${rule.section} ${rule.name}`;
    },
  },
};
</script>


<style lang="scss">
  $cloud-asset-compliance-header-height: 30px;

  .x-cloud-compliance {
    height: calc(100% - #{$cloud-asset-compliance-header-height});

    .cis-header {
      display: grid;
      grid-template-columns: 1fr 200px;

      .cis-score {
        grid-column: 2 ;
        grid-row: 1 / 3;
        justify-self: end;
      }

      .cis-row {
        display: flex;
        align-items: flex-end;
        line-height: 28px;
        margin-right: 16px;


        &.cis-type {
          grid-column: 1;
          grid-row: 1;

          .subtitle {
            font-size: 16px;
            font-weight: 400;
            color: $theme-black;
            margin-top: 12px;
            margin-right: 10px;
            width: 95px;
          }

          .cis-select {
            width: 450px;
          }
        }

        &.cis-filter {
          grid-column: 1;
          grid-row: 2;

          .filter-item {
            max-width: 230px;
            flex: 1 1 230px;

            .x-combobox {
              font-size: 14px;

              .v-input__control {
                border: 1px solid #DEDEDE !important;
              }
              .v-chip {
                max-width: 54%;
              }
            }
          }

          .table-filter {
            margin-right: 5px;
          }

          .search__reset {
            padding-top: 2px;
            width: 85px;
          }
          .failed-only {
            margin-left: 20px;
          }
          .cross-account {
            margin-left: 20px;
          }
        }
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
