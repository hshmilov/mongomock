<template>
  <div
    class="x-date-edit"
  >
    <ADatePicker
      v-show="!hide"
      v-model="selectedDate"
      :allow-clear="clearable"
      :disabled-date="checkDisabled"
      :placeholder="label"
      :format="dateFormat"
      :disabled="readOnly"
      :show-today="false"
      v-on="$listeners"
    />
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

import dayjs from 'dayjs';
import { DatePicker } from 'ant-design-vue';
import { DATE_FORMAT } from '@store/getters';
import { DEFAULT_DATE_FORMAT } from '@store/modules/constants';

export default {
  name: 'XDateEdit',
  components: {
    ADatePicker: DatePicker,
  },
  props: {
    value: {
      type: [String, Date],
      default: '',
    },
    readOnly: {
      type: Boolean, default: false,
    },
    clearable: {
      type: Boolean, default: true,
    },
    checkDisabled: {
      type: Function,
      default: () => false,
    },
    label: {
      type: String,
      default: 'Select Date',
    },
    hide: {
      type: Boolean,
      default: false,
    },
    formatResponse: {
      type: Boolean,
      default: true,
    },
  },
  computed: {
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    selectedDate: {
      get() {
        if (this.value) {
          return dayjs(this.value);
        }
        return null;
      },
      set(value) {
        let selectedDate;
        if (value) {
          selectedDate = this.formatResponse ? value.format(DEFAULT_DATE_FORMAT) : value;
        } else {
          selectedDate = '';
        }
        if (this.value === selectedDate) {
          return;
        }
        this.$emit('input', selectedDate);
      },
    },
  },
  methods: {
    handlePanelChange(value) {
      this.$emit('openChange', value);
    },
  },
};
</script>

<style lang="scss">
  .x-date-edit {
    .ant-input-disabled {
      color: $black-0;
      background-color: $grey-2;
      opacity: 0.6;
    }
  }
</style>
