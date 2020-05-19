<template>
  <XPage
    class="x-cloud-compliance-page"
    title="Cloud Asset Compliance Center"
    :beta="true"
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
          <div class="accounts-filter">
            <XCombobox
              v-if="accounts"
              v-model="filterAccounts"
              height="30"
              :selection-display-limit="2"
              :items="accounts"
              label="Accounts"
              multiple
              :allow-create-new="false"
              :hide-quick-selections="false"
              :menu-props="{maxWidth: 500}"
              @change="applySearchAndFilter"
            />
          </div>
          <XSwitch
            :checked="failedOnly"
            class="failed-only"
            label="Failed rules only"
            @change="toggleFailedSwitch"
          />
          <XButton
            class="search__reset"
            type="link"
            @click="resetAccountsFilter"
          >Reset</XButton>
        </div>
        <div class="cis-score">
          <XComplianceScore :score="getCurrentScore" />
        </div>
      </div>
      <XComplianceTable
        module="compliance"
        :cis-name="cisName"
        :data="filteredData"
        :loading="loading"
        :error="error"
        :accounts="accounts"
      />
    </div>
    <XComplianceTip
      v-if="featureFlags && !enabled"
    />
  </XPage>
</template>
<script>
import _filter from 'lodash/filter';
import _debounce from 'lodash/debounce';
import _get from 'lodash/get';
import _cloneDeep from 'lodash/cloneDeep';
import _has from 'lodash/has';
import { mapState, mapGetters } from 'vuex';

import XPage from '@axons/layout/Page.vue';
import XButton from '@axons/inputs/Button.vue';
import XCombobox from '@axons/inputs/combobox/index.vue';
import XSwitch from '@axons/inputs/Switch.vue';
import XComplianceTable from '@components/networks/compliance/ComplianceTable.vue';
import XComplianceTip from '@components/networks/compliance/ComplianceTip.vue';
import XComplianceScore from '@components/networks/compliance/ComplianceScore.vue';
import { fetchCompliance, fetchComplianceAccounts } from '@api/compliance';
import { IN_TRIAL } from '@store/modules/settings';
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
  },
  data() {
    return {
      cisName: 'aws',
      allCloudComplianceRules: [],
      accounts: null,
      filterAccounts: [],
      failedOnly: false,
      loading: false,
      error: null,
      complianceOptions: [
        { name: 'aws', title: 'CIS Amazon Web Services Foundations Benchmark V1.2' },
        /*{ name: 'azure', title: 'CIS Microsoft Azure Foundations Benchmark V1.1' },*/
      ],
      score: {
        totalScore: null, totalChecked: 0, totalFailed: 0, accounts: {},
      },
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
      const cisEnabled = _get(this.featureFlags, 'cloud_compliance.cis_enabled');
      return this.inTrial || cisEnabled;
    },
    getCurrentScore() {
      if (this.filterAccounts.length === 0) {
        return this.score.totalScore;
      }

      const res = {
        totalChecked: 0,
        totalFailed: 0,
      };
      this.filterAccounts.forEach((account) => {
        res.totalChecked += this.score.accounts[account].totalChecked;
        res.totalFailed += this.score.accounts[account].totalFailed;
      });

      return this.calculateFinalScore(res.totalChecked, res.totalFailed);
    },
  },
  mounted() {
    this.fetchAllData();
  },
  methods: {
    async fetchAllData() {
      this.loading = true;
      await this.fetchComplianceAccounts();
      await this.fetchComplianceRows();
      this.calculateScore();
      this.loading = false;
    },
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
      this.failedOnly = false;
    },
    applySearchAndFilter: _debounce(function applySearchAndFilter() {
      this.updateCurrentView();
    }, 250),
    async updateCurrentView() {
      this.loading = true;
      await this.fetchComplianceRows();
      this.loading = false;
    },
    complianceSelected(cis) {
      this.cisName = cis;
      this.fetchAllData();
    },
    calculateScore() {
      const { totalChecked, totalFailed, checkedAccounts } = this.iterateRulesForScoring();
      this.score.totalScore = this.calculateFinalScore(
        totalChecked,
        totalFailed,
      );
      this.score.totalChecked = totalChecked;
      this.score.totalFailed = totalFailed;
      this.score.accounts = checkedAccounts;
    },
    iterateRulesForScoring() {
      const accumulator = { totalChecked: 0, totalFailed: 0, checkedAccounts: {} };
      return this.allCloudComplianceRules.reduce(this.handleRuleScore, accumulator);
    },
    handleRuleScore(accumulator, rule) {
      const { account } = rule;
      const score = _cloneDeep(accumulator);

      if (!_has(score.checkedAccounts, account)) {
        score.checkedAccounts[account] = {
          totalChecked: 0,
          totalFailed: 0,
        };
      }

      if (this.isRuleFailed(rule.status)) {
        score.totalFailed += 1;
        score.checkedAccounts[account].totalFailed += 1;
      }
      score.totalChecked += 1;
      score.checkedAccounts[account].totalChecked += 1;

      return score;
    },
    calculateFinalScore(checked, failed) {
      const totalPassed = checked - failed;
      return Math.round((totalPassed / checked) * 100);
    },
    isRuleFailed(status) {
      return status === 'Failed' || status === 'No Data';
    },
    toggleFailedSwitch() {
      this.failedOnly = !this.failedOnly;
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

          .accounts-filter {
            width: 555px;
            .x-combobox {
              font-size: 14px;

              .v-input__control {
                border: 1px solid #DEDEDE !important;
              }
            }
          }
          .search__reset {
            padding-top: 2px;
            width: 85px;
          }
          .failed-only {
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
