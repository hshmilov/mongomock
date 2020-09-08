<template>
  <div
    class="main__filters-layer"
  >
    <AInputSearch
      v-if="search"
      v-model="data.search"
      class="filter-item search-input"
      placeholder="Search name"
      @keypress.enter="onApplyFilters"
    />
    <ADatePicker
      v-if="history"
      :value="formattedDate"
      class="filter-item history-input"
      placeholder="Select historical date"
      :allow-clear="false"
      :disabled-date="isDateDisabled"
      @change="onDateSelected"
    />
    <div
      class="filters-actions"
    >
      <XButton
        :disabled="!applyEnabled"
        @click="clear"
      >
        Clear Filters
      </XButton>
      <XButton
        type="primary"
        @click="onApplyFilters"
      >
        Show Results
      </XButton>
    </div>
  </div>
</template>

<script>
import { Input, DatePicker } from 'ant-design-vue';
import { mapState } from 'vuex';
import XButton from '@axons/inputs/Button.vue';
import dayjs from 'dayjs';
import _get from 'lodash/get';
import _isNil from 'lodash/isNil';

export default {
  name: 'XChartFilters',
  components: {
    AInputSearch: Input.Search,
    ADatePicker: DatePicker,
    XButton,
  },
  props: {
    filters: {
      type: Object,
      required: true,
    },
    search: {
      type: Boolean,
      default: false,
    },
    history: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      data: { ...this.filters },
    };
  },
  computed: {
    ...mapState({
      allowedDates(state) {
        const usersDiscoveryDatesObject = _get(state, 'constants.allowedDates.users', []);
        const devicesDiscoveryDatesObject = _get(state, 'constants.allowedDates.devices', []);

        const allowedDates = [
          ...Object.values(usersDiscoveryDatesObject),
          ...Object.values(devicesDiscoveryDatesObject),
        ].map((date) => dayjs(date).format('YYYY-MM-DD'));

        return new Set(allowedDates);
      },
    }),
    formattedDate() {
      return this.data.history ? dayjs(this.data.history) : undefined;
    },
    applyEnabled() {
      return Boolean(this.data.search || this.data.history);
    },
  },
  methods: {
    onDateSelected(date) {
      if (_isNil(date)) {
        this.data.history = undefined;
        return;
      }
      this.data.history = dayjs(date).format('YYYY-MM-DD');
    },
    onApplyFilters() {
      this.$emit('change', { ...this.data });
    },
    clear() {
      this.data = { search: undefined, history: undefined };
      this.$emit('change', { search: undefined, history: undefined });
    },
    isDateDisabled(date) {
      return !this.allowedDates.has(dayjs(date).format('YYYY-MM-DD'));
    },
  },
};
</script>
