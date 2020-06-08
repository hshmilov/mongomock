<template>
  <div class="score-card">
    <div class="score-header">
      <XButton
        v-if="canEditComplianceRules"
        type="link"
        @click="toggleRulesDialog"
      >
        <VIcon
          size="15"
          class="verticaldots-expression-handle"
        >$vuetify.icons.verticaldots</VIcon>
      </XButton>
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
      :visible="showRuleDialog"
      :all-cis-rules="allCisRules"
      v-model="activeRules"
      @close="toggleRulesDialog"
      @save-rules="$emit('save-rules', $event)"
      :custom-sort="customSort"
      :cis-title="cisTitle"
    />
  </div>
</template>

<script>

import { Icon, Tooltip } from 'ant-design-vue';
import XButton from '@axons/inputs/Button.vue';
import XComplianceActiveRules from './ComplianceActiveRules.vue';

export default {
  name: 'XComplianceScore',
  components: {
    ATooltip: Tooltip,
    AIcon: Icon,
    XButton,
    XComplianceActiveRules,
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
  },
  data() {
    return {
      scoreInfoTitle: 'The CIS Benchmark score is a the percentage of passed rules out of all checked rules.'
        + '\nThe score is calculated and aggregated on all accounts currently filtered.'
        + '\nOther filters will not affect the CIS benchmark score.',
      showRuleDialog: false,
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
    },
  },
};
</script>

<style scoped lang="scss">

    .score-card {
        width: 230px;
        height: 120px;
        background-color: white;
        border-radius: 4px;
        box-shadow: $textbox-shadow;
        border: solid 1px #ebedf8;

        .score-header {
          display: flex;
          height: 25px;
          width: 230px;
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
