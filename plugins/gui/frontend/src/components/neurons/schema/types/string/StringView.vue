<template>
  <img
    v-if="schema.format && schema.format === 'image'"
    :src="value"
    height="24"
    :style="{borderRadius: '50%'}"
    class="md-image"
    alt=""
  >
  <img
    v-else-if="schema.format && schema.format === 'logo'"
    :key="value"
    :src="require(`Logos/adapters/${value}.png`)"
    :alt="value"
    :title="title"
    height="24"
    class="logo md-image"
  >
  <XIcon
    v-else-if="schema.format && schema.format === 'icon'"
    :title="xIconTitle"
    :class="`icon-${value}`"
    v-bind="xIconProps"
  />
  <div
    v-else-if="schema.format && schema.format === 'status'"
    :title="$options.methods.formatDetails(value, schema, title, dateFormat)"
    :class="`status ${$options.methods.format(value, schema, dateFormat).
      toLowerCase().replace(' ', '-')}`"
  >
    &nbsp;
  </div>
  <div
    v-else-if="schema.format && schema.format === 'comments_tooltip' && value"
    :title="value"
  >
    <XIcon
      family="symbol"
      type="chat"
    />
  </div>
  <div
    v-else-if="value"
    :class="`table-td-content-${schema.name}`"
    :title="$options.methods.formatDetails(value, schema, title, dateFormat)"
  >{{ $options.methods.format(value, schema, dateFormat) }}</div>
  <div v-else>
    &nbsp;
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import { formatDate } from '@constants/utils';
import { DATE_FORMAT } from '@store/getters';
import { antIconsProperties } from '@constants/icons';
import _get from 'lodash/get';

export default {
  name: 'XStringView',
  props: {
    schema: {
      type: Object,
      required: true,
    },
    value: {
      type: [String, Number],
      default: '',
    },
    title: {
      type: String,
      default: null,
    },
  },
  computed: {
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    xIconProps() {
      if (this.ICONS_PROPERTIES_BY_VALUE[this.value]) {
        return this.ICONS_PROPERTIES_BY_VALUE[this.value];
      }
      return { family: 'symbol', type: this.value };
    },
    xIconTitle() {
      return _get(this.schema, `iconTooltip.${this.value}`, null);
    },
  },
  created() {
    this.ICONS_PROPERTIES_BY_VALUE = antIconsProperties;
  },
  methods: {
    formatUsername(value) {
      if (value.source) {
        return `${value.source}/${value.user_name}`;
      }
      return value.user_name;
    },
    formatDetails(value, schema, title, dateFormat) {
      if (title != null) {
        return title;
      }
      if (schema.format === 'date-time') {
        return formatDate(value, schema, dateFormat, true);
      }
      if (schema.format !== 'user') {
        return this.format(value, schema, dateFormat);
      }
      const parsedValue = JSON.parse(value);
      const username = this.formatUsername(parsedValue);
      const fullName = `${parsedValue.first_name} ${parsedValue.last_name}`.trim();
      const deleted = parsedValue.deleted ? ' (deleted)' : '';
      if (fullName) {
        return `${username} - ${fullName}${deleted}`;
      }
      return `${username}${deleted}`;
    },
    format(value, schema, dateFormat) {
      if (schema.cellRenderer) {
        return schema.cellRenderer(value);
      }
      if (schema.enum) {
        const enumSelectedOption = schema.enum.find((item) => item.name === value);
        return enumSelectedOption ? enumSelectedOption.title : value;
      }
      if (!schema.format) {
        return value;
      }
      if (schema.format === 'user') {
        return this.formatUsername(JSON.parse(value));
      }
      if (schema.format.includes('date') || schema.format.includes('time')) {
        return formatDate(value, schema, dateFormat);
      }
      if (schema.format === 'password') {
        return '********';
      }
      return value;
    },
  },
};
</script>

<style lang="scss" scoped>
  .x-icon {
    height: 16px;
    width: auto;
    display: flex;
  }
</style>
