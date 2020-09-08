<template>
  <div class="x-historical-date">
    <XDateEdit
      ref="date"
      :value="value"
      :check-disabled="isDateUnavailable"
      :hide="hide"
      label="Display by Date"
      @input="onInput"
      v-on="$listeners"
    />
  </div>
</template>


<script>
import dayjs from 'dayjs';
import { DEFAULT_DATE_FORMAT } from '@store/modules/constants';
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
  methods: {
    isDateUnavailable(date) {
      const isDateOutOfRange = date && date > dayjs().endOf('day');
      const isDateNotAllowed = date && !this.allowedDates[date.format(DEFAULT_DATE_FORMAT)];
      return isDateOutOfRange || !!isDateNotAllowed;
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
    overflow: hidden;
}
</style>
