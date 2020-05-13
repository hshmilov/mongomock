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
        <x-select
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
        <x-date-edit
          v-model="from"
          :check-disabled="checkDateAvailabilityFrom"
          :format="false"
          :clearable="false"
          label="From"
        />
        <x-date-edit
          v-model="to"
          :check-disabled="checkDateAvailabilityTo"
          :format="false"
          :clearable="false"
          label="To"
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
  import xSelect from '../../axons/inputs/select/Select.vue'
  import xDateEdit from '../schema/types/string/DateEdit.vue'
  import {validateNumber} from '../../../constants/validations'

  import { mapState, mapGetters } from 'vuex'
  import { TimelineTimeframesTypesEnum, TimelineTimeframesUnitsEnum } from '@constants/charts';
  import { FeatureFlagsEnum } from '@constants/feature_flags';

  export default {
    name: 'XSelectTimeframe',
    components: {
      xSelect, xDateEdit
    },
    props: {
      value: {
        type: Object,
        default: () => {}
      }
    },
    data() {
      return { TimelineTimeframesTypesEnum, maxDaysForLimitedQuery: 30 };
    },
    computed: {
      ...mapState({
        ...mapGetters({
          featureFlags: 'featureFlags',
        }),
        firstHistoricalDate (state) {
          return Object.values(state.constants.firstHistoricalDate)
            .map(dateStr => new Date(dateStr))
            .reduce((a, b) => {
              return (a < b) ? a : b
            }, new Date())
        },
        isUnlimitedHistory() {
          return this.featureFlags[FeatureFlagsEnum.query_timeline_range];
        },
       }),
      type: {
        get () {
          return this.value.type
        },
        set (type) {
          this.$emit('input', (type === TimelineTimeframesTypesEnum.absolute) ? {
            type, from: null, to: null
          } : {
            type, unit: TimelineTimeframesUnitsEnum.days.name, count: 7,
          })
        }
      },
      to: {
        get () {
          return this.value.to
        },
        set (to) {
          this.$emit('input', {...this.value, to})
        }
      },
      from: {
        get () {
          return this.value.from
        },
        set (from) {
          this.$emit('input', {...this.value, from})
        }
      },
      unit: {
        get () {
          return this.value.unit
        },
        set (unit) {
          this.$emit('input', {...this.value, unit})
        }
      },
      count: {
        get () {
          return this.value.count
        },
        set (count) {
          let daysCount = count;
          if (!this.isUnlimitedHistory) {
            if (Number.parseInt(daysCount, 10) > this.maxDaysForLimitedQuery) {
              daysCount = this.maxDaysForLimitedQuery;
            }
          } 
          this.$emit('input', { ...this.value, count: daysCount });
        }
      },
      isRangeAbsolute () {
        return this.type === TimelineTimeframesTypesEnum.absolute
      },
      relativeRangeUnits () {
        return [
          TimelineTimeframesUnitsEnum.days,
          TimelineTimeframesUnitsEnum.week,
          TimelineTimeframesUnitsEnum.month,
          TimelineTimeframesUnitsEnum.year,
        ];
      },
      isValid () {
        return (this.from != null && this.to !== null) || (this.count > 0 && this.unit)
      }
    },
    methods: {
      validateNumber,
      checkDateAvailabilityFrom (date) {
        let isPast = date < new Date(this.firstHistoricalDate)
        if (!this.to) {
          return isPast || date >= new Date()
        }
        return isPast || date >= this.to
      },
      checkDateAvailabilityTo (date) {
        let isFuture = date > new Date()
        if (!this.from) {
          return date < this.firstHistoricalDate || isFuture
        }
        return date <= this.from || isFuture
      }
    }
  }
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
      }
      .x-select-timeframe_config--limited {
        margin-top: 12px;
        label {
          margin-right: 16px;
        }
      }
    }
</style>
