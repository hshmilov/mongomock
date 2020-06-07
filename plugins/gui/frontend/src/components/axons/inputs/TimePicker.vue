<template>
  <VMenu
    ref="menu"
    v-model="timeModal"
    :close-on-content-click="false"
    :nudge-right="40"
    transition="scale-transition"
    offset-y
    offset-overflow
    class="x-time-picker"
  >
    <template v-slot:activator="{ on }">
      <div class="time-picker-wrapper">
        <div class="time-picker-text">
          <label v-if="label">{{ label }}</label>
          <VTextField
            :value="formattedTime"
            :error="timePickerError"
            :read-only="readOnly"
            @change="onInput"
            v-on="on"
          />
        </div>
        <span class="server-time">
          <XIcon
            family="symbol"
            type="info"
          />
          Timezone is UTC
        </span>
      </div>
    </template>
    <VTimePicker
      v-if="timeModal && !readOnly"
      v-model="timeValue"
      :ampm-in-title="true"
      :landscape="true"
      @click:minute="$refs.menu.save(value)"
    />
  </VMenu>
</template>

<script>
import dayjs from 'dayjs';
import XIcon from '@axons/icons/Icon';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import primitiveMixin from '../../../mixins/primitive';

dayjs.extend(customParseFormat);

export default {
  name: 'XTimePicker',
  components: { XIcon },
  mixins: [primitiveMixin],
  props: {
    value: {
      type: String,
      default: '',
    },
    readOnly: {
      type: Boolean, default: false,
    },
    label: {
      type: String,
      default: '',
    },
    schema: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      timeModal: false,
      error: false,
    };
  },
  computed: {
    formattedTime() {
      return dayjs(this.value, 'HH:mm').format('h:mma');
    },
    timePickerError() {
      return Boolean(this.error);
    },
    timeValue: {
      get() {
        return this.value;
      },
      set(value) {
        this.error = '';
        this.$emit('input', value);
        this.emitValidity();
      },

    },
  },
  methods: {
    onInput(selectedTime) {
      const time = dayjs(selectedTime, 'h:mma');
      if (!time.isValid()) {
        this.error = '\'Daily discovery time\' has an illegal value';
        this.valid = false;
      } else {
        this.error = '';
        this.valid = true;
        this.$emit('input', time.format('HH:mm'));
      }
      this.emitValidity();
    },
  },
};
</script>

<style lang="scss">
  .time-picker-text {
    input {
      font-size: 14px;
      padding-left: 3px;
    }
    .x-icon {
      font-size: 16px;
    }
  }
</style>
