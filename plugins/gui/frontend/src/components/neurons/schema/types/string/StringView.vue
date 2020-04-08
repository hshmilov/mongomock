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
  <md-icon
    v-else-if="schema.format && schema.format === 'icon'"
    :md-src="`/src/assets/icons/symbol/${value}.svg`"
    :class="`icon-${value}`"
  />
  <div
    v-else-if="schema.format && schema.format === 'status'"
    :title="$options.methods.formatDetails(value, schema, title)"
    :class="`status ${$options.methods.format(value, schema).
      toLowerCase().replace(' ', '-')}`"
  >
    &nbsp;
  </div>
  <div
    v-else-if="value"
    :class="`table-td-content-${schema.name}`"
    :title="$options.methods.formatDetails(value, schema, title)"
  >{{ $options.methods.format(value, schema) }}</div>
  <div v-else>
    &nbsp;
  </div>
</template>

<script>
import { formatDate } from '../../../../../constants/utils';

const UPDATED_BY_FIELD = 'updated_by';

export default {
  name: 'XStringView',
  data() {
    return {
      foo: 'bac',
    };
  },
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
  methods: {
    formatUsername(value) {
      if (value.source) {
        return `${value.source}/${value.username}`;
      }
      return value.username;
    },
    formatDetails(value, schema, title) {
      if (title != null) {
        return title;
      }
      if (schema.name !== UPDATED_BY_FIELD) {
        return this.format(value, schema);
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
    format(value, schema) {
      if (schema.cellRenderer) {
        return schema.cellRenderer(value);
      }
      if (schema.name === UPDATED_BY_FIELD) {
        return this.formatUsername(JSON.parse(value));
      }
      if (!schema.format) return value;
      if (schema.format.includes('date') || schema.format.includes('time')) {
        return formatDate(value, schema);
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
