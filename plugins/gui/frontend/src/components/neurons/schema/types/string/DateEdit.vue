<template>
  <MdField v-if="readOnly">
    <MdInput
      type="text"
      disabled
    />
  </MdField>
  <div
    v-else
    class="x-date-edit"
    :class="{labeled: label}"
  >
    <MdDatepicker
      v-show="!hide || datepickerActive"
      ref="date"
      v-model="selectedDate"
      :md-disabled-dates="checkDisabled"
      :md-immediately="true"
      :md-debounce="500"
      :class="{'no-icon': minimal, 'no-clear': !clearable}"
    >
      <label v-if="label">{{ label }}</label>
    </MdDatepicker>
    <XButton
      v-if="value && clearable"
      type="link"
      @click="onClear"
    >X</XButton>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import _get from 'lodash/get';
import dayjs from 'dayjs';
import XButton from '../../../../axons/inputs/Button.vue';
import { DATE_FORMAT } from '../../../../../store/getters';
import { DEFAULT_DATE_FORMAT } from '../../../../../store/modules/constants';

export default {
  name: 'XDateEdit',
  components: {
    XButton,
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
    minimal: {
      type: Boolean, default: false,
    },
    checkDisabled: {
      type: Function,
      default: () => false,
    },
    label: {
      type: String,
      default: '',
    },
    hide: {
      type: Boolean,
      default: false,
    },
  },
  created() {
    this.$material.locale.dateFormat = this.dateFormat;
  },
  computed: {
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    selectedDate: {
      get() {
        return this.value;
      },
      set(value) {
        let selectedDate = value;
        if (selectedDate && typeof selectedDate !== 'string') {
          selectedDate = dayjs(selectedDate).format(DEFAULT_DATE_FORMAT);
        } else if (!selectedDate) {
          this.$refs.date.modelDate = '';
        }
        if (this.value === selectedDate) {
          return;
        }
        this.$emit('input', selectedDate);
      },
    },
    datepickerActive() {
      if (!this.$refs.date) return false;
      return this.$refs.date.showDialog;
    },
  },
  methods: {
    onClear() {
      this.selectedDate = (typeof this.value === 'string') ? '' : null;
    },
  },
};
</script>

<style lang="scss">
    .x-date-edit {
        display: flex;
        .md-datepicker.md-clearable {
            .md-input-action {
                visibility: hidden;
            }
        }
        &:not(.labeled) .md-datepicker.md-field {
            width: auto;
            padding-top: 0;
            min-height: auto;
            margin-bottom: 0;
        }
        .x-button.ant-btn-link {
            margin-left: -16px;
            margin-bottom: 0;
            z-index: 100;
        }
    }
</style>
