<template>
  <div class="score-card">
    <div class="score-header">
      <ADropdown
        v-if="canEditComplianceRules && !lockComplianceActions"
        :trigger="!canEditComplianceRules?['']:['click']"
        placement="bottomRight"
        :disabled="!canEditComplianceRules"
        :visible="dropDownVisible"
        overlay-class-name="score-card-settings-menu"
        @visibleChange="openCloseMenu"
      >
        <XButton
          type="link"
          @trigger="openCloseMenu"
        >
          <XIcon
            family="symbol"
            type="verticalDots"
          />
        </XButton>
        <AMenu
          slot="overlay"
        >
          <AMenuItem
            id="edit_score_settings"
            key="edit_score_settings"
            @click="toggleRulesDialog"
          >
            Configure Benchmark Rules
          </AMenuItem>
        </AMenu>
      </ADropdown>

    </div>
    <div class="score-body">
      <div class="score-content">
        <span
          v-if="displaySort"
          class="score-value"
          :class="`score-${getScoreClass}`"
        > {{ score }}% </span>
        <span class="score-info">
          CIS Benchmark Score
        </span>
        <ATooltip
          :title="scoreInfoTitle"
          placement="bottom"
        >
          <AIcon
            type="info-circle"
            theme="twoTone"
          />
        </ATooltip>
      </div>
    </div>
    <XComplianceActiveRules
      v-if="canEditComplianceRules"
      v-model="activeRules"
      :visible="showRuleDialog"
      :all-cis-rules="allCisRules"
      :custom-sort="customSort"
      :cis-title="cisTitle"
      @close="toggleRulesDialog"
      @save-rules="$emit('save-rules', $event)"
    />
  </div>
</template>

<script>

import {
  Icon, Tooltip, Dropdown, Menu,
} from 'ant-design-vue';
import XComplianceActiveRules from './ComplianceActiveRules.vue';

export default {
  name: 'XComplianceScore',
  components: {
    ATooltip: Tooltip,
    AIcon: Icon,
    XComplianceActiveRules,
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
  },
  props: {
    value: {
      type: Array,
      default: () => [],
    },
    score: {
      type: Number,
      default: 0,
    },
    allCisRules: {
      type: Array,
      default: () => [],
    },
    customSort: {
      type: Function,
      default: null,
    },
    cisTitle: {
      type: String,
      default: '',
    },
    lockComplianceActions: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      scoreInfoTitle: 'The CIS Benchmark score is a the percentage of passed rules out of all checked rules.'
        + '\nThe score is calculated and aggregated on all accounts currently filtered.'
        + '\nOther filters will not affect the CIS benchmark score.',
      showRuleDialog: false,
      dropDownVisible: false,
    };
  },
  computed: {
    getScoreClass() {
      if (this.score >= 70) return 'passed';
      if (this.score >= 50) return 'dangerous';
      return 'failed';
    },
    displaySort() {
      return this.score !== null && this.score >= 0;
    },
    activeRules: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit('input', value);
      },
    },
    canEditComplianceRules() {
      return this.$can(this.$permissionConsts.categories.Compliance, this.$permissionConsts.actions.Update);
    },
  },
  methods: {
    toggleRulesDialog() {
      this.showRuleDialog = !this.showRuleDialog;
      this.dropDownVisible = false;
    },
    openCloseMenu() {
      this.dropDownVisible = !this.dropDownVisible;
    },
  },
};
</script>

<style scoped lang="scss">

    .score-card {
        width: 215px;
        height: 120px;
        background-color: white;
        border-radius: 4px;
        box-shadow: $textbox-shadow;
        border: solid 1px #ebedf8;

        .score-header {
          display: flex;
          height: 25px;
          width: 215px;
          flex-flow: row-reverse;

          > button {
            padding-right: 5px;
          }
        }

        .score-body {
          display: flex;
          justify-content: center;

          .score-content {
            margin: auto;

            .score-value {
              display: block;
              text-align: center;
              font-size: 25px;
              font-weight: 400;

              &.score-passed {
                color: $indicator-success;
              }

              &.score-dangerous {
                color: $indicator-dangerous;
              }

              &.score-failed {
                color: $indicator-error;
              }
            }

            .score-info {
              font-size: 14px;
              color: #9fa9ba;
              font-weight: 300;
            }
          }
        }

    }

</style>
