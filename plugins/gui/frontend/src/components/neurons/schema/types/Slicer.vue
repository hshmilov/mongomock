<template>
  <div class="x-slicer">
    <slot :sliced="slicedData" />
    <div
      v-if="remainder"
      class="remainder"
      @mouseover.stop="onHoverRemainder"
      @mouseleave="onLeaveRemainder"
    >
      <span>+{{ remainder }}</span>
      <x-tooltip v-if="inHover">
        <x-table
          slot="body"
          v-bind="tooltipTable"
        />
      </x-tooltip>
    </div>
  </div>
</template>

<script>
  import xTable from '../../../axons/tables/Table.vue'
  import xTooltip from '../../../axons/popover/Tooltip.vue'
  import {isObjectListField } from '../../../../constants/utils'

  import {mapState} from 'vuex'

  export default {
    name: 'XSlicer',
    components: {
      xTable, xTooltip
    },
    props: {
      schema: {
        type: Object,
        required: true
      },
      value: {
        type: [String, Number, Boolean, Array, Object],
        default: undefined
      }
    },
    data () {
      return {
        inHover: false
      }
    },
    computed: {
      ...mapState({
        defaultColumnLimit (state) {
          if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return 0
          return state.configuration.data.system.defaultColumnLimit
        }
      }),
      limit () {
        if (!Array.isArray(this.value) || this.schema.name === 'adapters') {
          return 0
        }
        if (isObjectListField(this.schema)) {
          return 1
        }
        return this.defaultColumnLimit
      },
      slicedData () {
        if (!this.limit) {
          return this.value
        }
        return this.value.slice(0, this.limit)
      },
      remainder () {
        return this.limit && this.value.length > this.limit ? this.value.length - this.limit : 0
      },
      tooltipTable () {
        let schema = { ...this.schema }
        if (schema.type === 'array' && !Array.isArray(schema.items) && !isObjectListField(schema)) {
          schema = { ...schema, ...schema.items }
        }
        if (this.value.length > 500) {
          schema.title += ' (first 500 results)'
        }
        return {
          fields: [schema],
          data: this.value.slice(0, 500),
          colFilters: {
            [schema.name]: this.filter
          },
          filterable: false
        }
      }
    },
    methods: {
      onHoverRemainder () {
        this.inHover = true
      },
      onLeaveRemainder () {
        this.inHover = false
      }
    }
  }
</script>

<style lang="scss">
  .x-slicer {
    display: flex;
    align-items: center;
    .remainder {
      position: relative;
      height: 20px;
      padding: 0 4px;
      border-radius: 4px;
      background: rgba($theme-orange, .4);
      color: initial;
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      .x-tooltip {
        top: 20px;
        left: 0;
        &.left {
          left: auto;
        }
        &.top {
          top: auto;
        }
      }
    }
  }
</style>