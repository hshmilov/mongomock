<template>
  <div class="x-select-timeframe">
    <div
      v-if="isUnlimitedHistory"
      class="x-select-timeframe_config--unlimited"
    >
      <input
        id="range_relative"
        v-model="type"
        type="radio"
        :value="TimelineTimeframesTypesEnum.relative"
      >
      <label for="range_relative">Show results in the last</label>
      <template v-if="!isRangeAbsolute">
        <input
          v-model.number="count"
          type="number"
          @keypress="validateNumber"
        >
        <XSelect
          v-model="unit"
          :options="relativeRangeUnits"
          placeholder="Units"
        />
      </template>
      <div
        v-else
        class="grid-span2"
      />
      <input
        id="range_absolute"
        v-model="type"
        type="radio"
        :value="TimelineTimeframesTypesEnum.absolute"
      >
      <label for="range_absolute">Show results in date range</label>
      <template v-if="isRangeAbsolute">
        <ARangePicker
          v-model="range"
          :disabled-date="disabledDate"
          :allow-clear="false"
        />
      </template>
      <div
        v-else
        class="grid-span2"
      />
    </div>
    <div
      v-else
      class="x-select-timeframe_config--limited"
    >
      <label for="range_relative">Show results in the last (days)</label>
      <input
        v-model.number="count"
        type="number"
        :max="maxDaysForLimitedQuery"
        @keypress="validateNumber"
      >
    </div>
  </div>
</template>

<script>
import { mapState, mapGetters } from 'vuex';
import { DatePicker } from 'ant-design-vue';
import { TimelineTimeframesTypesEnum, TimelineTimeframesUnitsEnum } from '@constants/charts';
import { validateNumber } from '@constants/validations';
import { FeatureFlagsEnum } from '@constants/feature_flags';
import { DEFAULT_DATE_FORMAT } from '@store/modules/constants';
import XSelect from '@axons/inputs/select/Select.vue';
import dayjs from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';
import minMax from 'dayjs/plugin/minMax';

dayjs.extend(isBetween);
dayjs.extend(minMax);

export default {
  name: 'XSelectTimeframe',
  components: {
    XSelect, ARangePicker: DatePicker.RangePicker,
  },
  props: {
    value: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      TimelineTimeframesTypesEnum,
      maxDaysForLimitedQuery: 30,
      selectedFrom: false,
      selectedTo: false,
    };
  },
  computed: {
    ...mapState({
      ...mapGetters({
        featureFlags: 'featureFlags',
      }),
      firstHistoricalDate(state) {
        return dayjs.min(Object.values(state.constants.firstHistoricalDate)
          .map((date) => dayjs(date)));
      },
      isUnlimitedHistory() {
        return this.featureFlags[FeatureFlagsEnum.query_timeline_range];
      },
    }),
    type: {
      get() {
        return this.value.type;
      },
      set(type) {
        this.$emit('input', (type === TimelineTimeframesTypesEnum.absolute) ? {
          type, from: null, to: null,
        } : {
          type, unit: TimelineTimeframesUnitsEnum.days.name, count: 7,
        });
      },
    },
    range: {
      get() {
        if (this.value.from && this.value.to) {
          return [dayjs(this.value.from), dayjs(this.value.to)];
        }
        return [];
      },
      set(values) {
        this.$emit('input', {
          ...this.value,
          from: values[0].format(DEFAULT_DATE_FORMAT),
          to: values[1].format(DEFAULT_DATE_FORMAT),
        });
      },
    },
    unit: {
      get() {
        return this.value.unit;
      },
      set(unit) {
        this.$emit('input', { ...this.value, unit });
      },
    },
    count: {
      get() {
        return this.value.count;
      },
      set(count) {
        let daysCount = count;
        if (!this.isUnlimitedHistory) {
          if (Number.parseInt(daysCount, 10) > this.maxDaysForLimitedQuery) {
            daysCount = this.maxDaysForLimitedQuery;
          }
        }
        this.$emit('input', { ...this.value, count: daysCount });
      },
    },
    isRangeAbsolute() {
      return this.type === TimelineTimeframesTypesEnum.absolute;
    },
    relativeRangeUnits() {
      return [
        TimelineTimeframesUnitsEnum.days,
        TimelineTimeframesUnitsEnum.week,
        TimelineTimeframesUnitsEnum.month,
        TimelineTimeframesUnitsEnum.year,
      ];
    },
    isValid() {
      return (this.value.from != null && this.value.to !== null) || (this.count > 0 && this.unit);
    },
  },
  methods: {
    validateNumber,
    disabledDate(date) {
      return date && !(date.isBetween(this.firstHistoricalDate, dayjs(), 'days', '[]'));
    },
  },
};
</script>

<style lang="scss">
    .x-select-timeframe {
      .x-select-timeframe_config--unlimited {
        margin-top: 12px;
        display: grid;
        grid-template-columns: 20px 180px auto auto;
        grid-gap: 8px;
        align-items: center;
        grid-template-rows: 32px 32px;
        min-width: 0;

        .x-select-trigger {
            line-height: 24px;
            height: 24px;
        }
        .ant-calendar-picker {
          width: 100%;
        }
      }
      .x-select-timeframe_config--limited {
        margin-top: 12px;
        label {
          margin-right: 16px;
        }
      }
    }
</style>
