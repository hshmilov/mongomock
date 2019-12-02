<template functional>
  <img
    v-if="props.schema.format && props.schema.format === 'image'"
    :src="props.value"
    height="24"
    :style="{borderRadius: '50%'}"
    class="md-image"
  >
  <img
    v-else-if="props.schema.format && props.schema.format === 'logo'"
    :src="require(`Logos/adapters/${props.value}.png`)"
    :alt="props.value"
    height="24"
    class="logo md-image"
  >
  <md-icon
    v-else-if="props.schema.format && props.schema.format === 'icon'"
    :md-src="`/src/assets/icons/symbol/${props.value}.svg`"
    :class="`icon-${props.value}`"
  />
  <div
    v-else-if="props.value"
    :title="$options.methods.formatDetails(props.value, props.schema)"
  >{{ $options.methods.format(props.value, props.schema) }}</div>
  <div v-else>&nbsp;</div>
</template>

<script>
  import { formatDate } from '../../../../../constants/utils'

  const UPDATED_BY_FIELD = 'updated_by'

  export default {
    name: 'XStringView',
    props: {
      schema: {
        type: Object,
        required: true
      },
      value: {
        type: String,
        default: ''
      }
    },
    methods: {
      formatUsername(value) {
        if (value.source) {
          return `${value.source}/${value.username}`
        }
        return value.username
      },
      formatDetails(value, schema) {
        if (schema.name !== UPDATED_BY_FIELD) {
          return
        }
        value = JSON.parse(value)
        const username = this.formatUsername(value)
        const fullName = `${value.first_name} ${value.last_name}`.trim()
        const deleted = value.deleted? ' (deleted)' : ''
        if (fullName) {
          return `${username} - ${fullName}${deleted}`
        }
        return `${username}${deleted}`
      },
      format(value, schema) {
        if (schema.name === UPDATED_BY_FIELD) {
          return this.formatUsername(JSON.parse(value))
        }
        if (!schema.format) return value
        if (schema.format.includes('date') || schema.format.includes('time')) {
          return formatDate(value, schema)
        }
        if (schema.format === 'password') {
          return '********'
        }
        return value
      }
    }
  };
</script>

<style lang="scss" scoped>
  .md-icon {
    height: 16px;
    width: auto;
    display: flex;
  }
</style>