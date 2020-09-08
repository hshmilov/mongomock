<template>
  <div class="x-table-search">
    <XSearchInput
      v-model="searchValue"
      :placeholder="`Search ${searchPlaceholderText}...`"
      @keyup.enter.native="onConfirmSearch"
    />
    <div
      v-if="enableDateSearch"
      class="date-search"
    >
      <XButton
        type="link"
        @click="resetSearch"
      >
        Reset
      </XButton>
      <ARangePicker
        v-model="dateRangeProxy"
        :format="dateFormat + ' HH:mm:ss'"
        :show-time="defaultTimePickerValue"
        :disabled-date="disabledDate"
        :default-picker-value="defaultPickerValue"
        @change="rangePickerChange"
        @ok="rangePickerOk"
        @openChange="rangePickerOpenStatus"
      />
    </div>
  </div>
</template>

<script>
import { DatePicker } from 'ant-design-vue';
import { mapGetters, mapMutations } from 'vuex';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import dayjs from 'dayjs';
import _capitalize from 'lodash/capitalize';
import { DATE_FORMAT } from '@store/getters';
import XButton from '@axons/inputs/Button.vue';
import XSearchInput from './SearchInput.vue';

export default {
  name: 'XTableSearchFilters',
  components: {
    XButton,
    XSearchInput,
    ARangePicker: DatePicker.RangePicker,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    view: {
      type: Object,
      required: true,
    },
    searchPlaceholder: {
      type: String,
      default: '',
    },
    enableDateSearch: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      okClicked: false,
      dateRangeProxy: [],
      defaultPickerValue: [
        dayjs().subtract(1, 'month'),
        dayjs(),
      ],
      defaultTimePickerValue: {
        format: 'HH:mm',
        defaultValue: [
          dayjs('00:00:00', 'HH:mm:ss'),
          dayjs('23:59:59', 'HH:mm:ss')],
      },
    };
  },
  computed: {
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    searchValue: {
      get() {
        return this.view.query.search;
      },
      set(search) {
        this.updateView({
          module: this.module,
          view: {
            page: 0,
            query: {
              filter: '',
              search,
            },
          },
        });
      },
    },
    searchPlaceholderText() {
      if (this.searchPlaceholder) return this.searchPlaceholder;
      return _capitalize(this.module);
    },
  },
  mounted() {
    this.resetRangeProxy();
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    onConfirmSearch() {
      this.$emit('search');
    },
    disabledDate(current) {
      // Can not select days after today
      return current && current > dayjs().endOf('day');
    },
    rangePickerChange(values) {
      if (!values.length) {
        this.updateDateSearchValues(null, null);
        this.onConfirmSearch();
      }
    },
    rangePickerOk(values) {
      this.okClicked = true;
      const dates = values.map((date) => date.utc().format());
      this.updateDateSearchValues(dates[0], dates[1]);
      this.onConfirmSearch();
    },
    rangePickerOpenStatus(status) {
      if (!status) {
        if (!this.okClicked) {
          this.resetRangeProxy();
        }
        this.okClicked = false;
      }
    },
    updateDateSearchValues(dateFrom, dateTo) {
      this.updateView({
        module: this.module,
        view: {
          page: 0,
          queryStrings: {
            date_from: dateFrom,
            date_to: dateTo,
          },
        },
      });
    },
    resetSearch() {
      this.dateRangeProxy = [];
      this.updateView({
        module: this.module,
        view: {
          page: 0,
          query: {
            filter: '',
            search: '',
          },
          queryStrings: {
            date_from: null,
            date_to: null,
          },
        },
      });
      this.onConfirmSearch();
    },
    resetRangeProxy() {
      const { queryStrings } = this.view;
      if (queryStrings && queryStrings.date_from && queryStrings.date_to) {
        this.dateRangeProxy = [dayjs(queryStrings.date_from), dayjs(queryStrings.date_to)];
      } else {
        this.dateRangeProxy = [];
      }
    },
  },
};
</script>

<style lang="scss">
.x-table-search {
  display: flex;
  background: $grey-0;
  .x-search-input {
    flex-grow: 1;
  }
  .date-search {
    margin-left: 10px;
  }
  ~ .x-table {
    height: calc(100% - 75px);
  }
}
</style>
