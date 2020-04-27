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
    height="24"
    class="logo md-image"
  >
  <MdIcon
    v-else-if="schema.format && schema.format === 'icon'"
    :md-src="`/src/assets/icons/symbol/${value}.svg`"
    :class="`icon-${value}`"
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
import _get from 'lodash/get';
import { formatDate } from '../../../../../constants/utils';
import { DATE_FORMAT } from '../../../../../store/getters';

export default {
  name: 'XStringView',
  props: {
    schema: {
      type: Object,
      required: true,
    },
    value: {
      type: String,
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
  },
  methods: {
    formatUsername(value) {
      if (value.source) {
        return `${value.source}/${value.username}`;
      }
      return value.username;
    },
    formatDetails(value, schema, title, dateFormat) {
      if (title != null) {
        return title;
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
      if (schema.format === 'user') {
        return this.formatUsername(JSON.parse(value));
      }
      if (!schema.format) return value;
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
  .md-icon {
    height: 16px;
    width: auto;
    display: flex;
  }
</style>
