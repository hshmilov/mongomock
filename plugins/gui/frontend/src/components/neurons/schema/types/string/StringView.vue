<template>
  <img
    v-if="schema.format && schema.format === 'image'"
    :src="value"
    height="24"
    :style="{borderRadius: '50%'}"
    class="md-image"
  >
  <img
    v-else-if="schema.format && schema.format === 'logo'"
    :src="require(`Logos/adapters/${value}.png`)"
    height="24"
    class="logo md-image"
  >
  <svg-icon
    v-else-if="schema.format && schema.format === 'icon'"
    :name="`symbol/${value}`"
    :original="true"
    height="16"
  ></svg-icon>
  <div v-else-if="hyperlink">
    <a
      :href="hyperlinkHref"
      @click="onClickLink(hyperlink)"
    >{{ processedData }}</a>
  </div>
  <md-chip
    v-else-if="schema.format && schema.format === 'tag'"
    class="tag"
  >{{ processedData }}</md-chip>
  <div
    v-else-if="processedData"
    :title="completeData"
  >{{ processedData }}</div>
  <div v-else>&nbsp;</div>
</template>

<script>
  import hyperlinkMixin from '../hyperlink.js'
  import { formatDate, includesIgnoreCase } from '../../../../../constants/utils'

  export default {
    name: 'XStringView',
    mixins: [hyperlinkMixin],
    props: {
      schema: {
        type: Object,
        required: true
      },
      value: {
        type: [String, Array],
        default: ''
      },
      filter: {
        type: String,
        default: ''
      }
    },
    computed: {
      filteredData () {
        if (!this.filter) {
          return this.value
        }
        if (Array.isArray(this.value)) {
          return this.value.filter(item => includesIgnoreCase(item, this.filter))
        }
        return includesIgnoreCase(this.value, this.filter) ? this.value : ''
      },
      processedData () {
        if (Array.isArray(this.filteredData)) {
          let remainder = this.filteredData.length - 2
          return this.filteredData.slice(0, 2).map(item => this.format(item))
                  .join(', ') + (remainder > 0 ? ` +${remainder}` : '')
        }
        return this.format(this.filteredData)
      },
      completeData () {
        if (Array.isArray(this.filteredData)) {
          return this.filteredData.map(item => this.format(item)).join(', ')
        }
        return this.format(this.filteredData)
      }
    },
    methods: {
      format (value) {
        if (!this.schema.format) return value
        if (this.schema.format.includes('date') || this.schema.format.includes('time')) {
          if (!value) return ''
          return formatDate(value, this.schema)
        }
        if (this.schema.format === 'password') {
          return '********'
        }
        return value
      }
    }
  }
</script>

<style lang="scss">
</style>