<template>
  <div class="x-historical-date">
    <XDateEdit
      ref="date"
      :value="value"
      :check-disabled="isDateUnavailable"
      :hide="hide"
      label="Display by Date"
      @input="onInput"
    />
  </div>
</template>


<script>
import { mapState } from 'vuex';
import XDateEdit from '../schema/types/string/DateEdit.vue';

export default {
  name: 'XHistoricalDate',
  components: {
    XDateEdit,
  },
  props: {
    value: {
      type: [String, Date],
      default: null,
    },
    module: {
      type: String,
      default: '',
    },
    hide: {
      type: Boolean,
      default: false,
    },
    allowedDates: {
      type: Object,
      default: () => ({}),
    },
  },
  computed: {
    ...mapState({
      firstHistoricalDate(state) {
        let historicalDate = null;
        if (this.module) {
          historicalDate = state.constants.firstHistoricalDate[this.module];
        } else {
          historicalDate = Object.values(state.constants.firstHistoricalDate)
            .reduce((a, b) => ((new Date(a) < new Date(b)) ? a : b), new Date());
        }
        historicalDate = new Date(historicalDate);
        historicalDate.setDate(historicalDate.getDate() - 1);
        return historicalDate;
      },
    }),
  },
  methods: {
    isDateUnavailable(date) {
      // return true if date is unavailable, return false if date is available
      // if date smaller then the first day we have historical or bigger than today disable it!
      const currentDate = new Date().toISOString();
      const dateToCheck = date.toISOString();
      if (dateToCheck < this.firstHistoricalDate.toISOString() || dateToCheck > currentDate) {
        return true;
      }
      return (this.allowedDates && !this.allowedDates[dateToCheck.substring(0, 10)]);
    },
    onInput(historical) {
      this.$emit('input', historical);
    },
  },
};
</script>


<style lang="scss">
    .x-historical-date {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 8px;
        overflow: hidden;

        .md-datepicker {
            margin: -20px 0 0 0;
            min-height: auto;

            .md-input {
                max-width: 160px;
                padding-right: 10px;
            }
        }
    }
</style>
