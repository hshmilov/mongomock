<template>
  <div class="score-card">
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
</template>

<script>

import { Icon, Tooltip } from 'ant-design-vue';

export default {
  name: 'XComplianceScore',
  components: {
    ATooltip: Tooltip,
    AIcon: Icon,
  },
  props: {
    score: {
      type: Number,
      default: null,
    },
  },
  computed: {
    getScoreClass() {
      if (this.score >= 70) return 'passed';
      if (this.score >= 50) return 'dangerous';
      return 'failed';
    },
    displaySort() {
      return this.score && this.score >= 0;
    },
  },
  data() {
    return {
      scoreInfoTitle: 'The CIS Benchmark score is a the percentage of passed rules out of all checked rules.'
        + '\nThe score is calculated and aggregated on all accounts currently filtered.'
        + '\nOther filters will not affect the CIS benchmark score.',
    };
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

</style>
