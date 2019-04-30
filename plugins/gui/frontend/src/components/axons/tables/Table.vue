<template>
  <table class="x-striped-table">
    <thead>
      <tr class="x-row clickable">
        <th
          v-if="value"
          class="w-14"
        >
          <x-checkbox
            :data="allSelected"
            :indeterminate="partSelected"
            @change="onSelectAll"
          />
        </th>
        <th v-if="expandable">&nbsp;</th>
        <th
          v-for="field in dataField"
          :key="field.name"
          nowrap
          :class="{sortable: onClickCol}"
          @click="clickCol(field.name)"
          @keyup.enter.stop="clickCol(field.name)"
        >
          <img
            v-if="field.logo"
            class="logo md-image"
            :src="require(`Logos/adapters/${field.logo}.png`)"
            height="20"
            :alt="field.title"
          >{{ field.title }}<div
            v-if="onClickCol"
            :class="`x-sort ${sortClass(field.name)}`"
          />
        </th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="item in data"
        :id="item[idField]"
        :key="item[idField]"
        class="x-row"
        :class="{ clickable: onClickRow && !readOnly.includes(item[idField]) }"
        @click="clickRow(item[idField])"
      >
        <td
          v-if="value"
          class="w-14"
        >
          <x-checkbox
            v-model="selected"
            :value="item[idField]"
            :read-only="readOnly.includes(item[idField])"
            @change="onSelect"
          />
        </td>
        <td v-if="expandable">
          <md-icon
            v-if="expanded.includes(item[idField])"
            @click.native.stop="collapseRow(item[idField])
            ">expand_less</md-icon>
          <md-icon
            v-else
            @click.native.stop="expandRow(item[idField])"
          >expand_more</md-icon>
        </td>
        <td
          v-for="field in dataField"
          :key="field.name"
          nowrap
        >
          <component
            :is="field.type"
            :schema="field"
            :value="processDataValue(item, field)"
          />
          <div class="details-container">
            <transition name="slide-fade">
              <div
                v-if="expandable && expanded.includes(item[idField])"
                class="details"
              >
                <component
                  v-for="(detail, index) in getDetails(item, field)"
                  :key="index"
                  :is="field.type"
                  :schema="field"
                  :value="detail"
                  class="detail"
                />
              </div>
            </transition>
          </div>
        </td>
      </tr>
      <template v-if="pageSize">
        <tr
          v-for="n in pageSize - data.length"
          :key="n"
          class="x-row"
        >
          <td v-if="value">&nbsp;</td>
          <td v-if="expandable">&nbsp;</td>
          <td
            v-for="field in fields"
            :key="field.name"
          >&nbsp;</td>
        </tr>
      </template>
    </tbody>
  </table>
</template>

<script>
  import xCheckbox from '../inputs/Checkbox.vue'
  import string from '../../neurons/schema/types/string/StringView.vue'
  import number from '../../neurons/schema/types/numerical/NumberView.vue'
  import integer from '../../neurons/schema/types/numerical/IntegerView.vue'
  import bool from '../../neurons/schema/types/boolean/BooleanView.vue'
  import file from '../../neurons/schema/types/array/FileView.vue'
  import array from '../../neurons/schema/types/array/ArrayTableView.vue'

  export default {
    name: 'XTable',
    components: { xCheckbox, string, integer, number, bool, file, array },
    props: {
      fields: {
        type: Array,
        required: true
      },
      data: {
        type: [Object, Array],
        required: true
      },
      pageSize: {
        type: Number,
        default: null
      },
      sort: {
        type: Object,
        default: () => {
          return { field: '', desc: true }
        }
      },
      idField: {
        type: String,
        default: 'uuid'
      },
      value: {
        type: [Object, Array],
        default: undefined
      },
      expandable: {
        type: Boolean,
        default: false
      },
      onClickRow: {
        type: Function,
        default: undefined
      },
      onClickCol: {
        type: Function,
        default: undefined
      },
      onClickAll: {
        type: Function,
        default: undefined
      },
      readOnly: {
        type: Array,
        default: () => []
      }
    },
    data () {
      return {
        selected: [],
        expanded: []
      }
    },
    computed: {
      ids () {
        return this.data.map(item => item[this.idField])
      },
      allSelected () {
        return this.selected.length && this.selected.length === this.data.length
      },
      partSelected () {
        return this.selected.length && this.selected.length < this.data.length
      },
      dataField () {
        return this.fields.map(field => {
          return {
            ...field,
            path: (field.path ? field.path : []).concat([field.name])
          }
        })
      }
    },
    watch: {
      value (newValue) {
        this.selected = [...newValue]
      }
    },
    methods: {
      clickRow (id) {
        if (!this.onClickRow || this.readOnly.includes(id)) return

        this.onClickRow(id)
      },
      clickCol (name) {
        if (!this.onClickCol) return

        this.onClickCol(name)

      },
      sortClass (name) {
        if (this.sort.field !== name) return ''
        if (this.sort.desc) return 'down'
        return 'up'
      },
      onSelectAll (isSelected) {
        if (isSelected && !this.selected.length) {
          this.selected = [...this.ids.filter(id => !this.readOnly.includes(id))]
        } else {
          this.selected = []
        }
        this.$emit('input', this.selected)
        if (this.onClickAll) {
          this.onClickAll(isSelected)
        }
      },
      onSelect () {
        this.$emit('input', this.selected)
      },
      processDataValue (item, field) {
        if (!field.name) return item
        let value = item[field.name]
        if (Array.isArray(value) && this.sort && field.name === this.sort.field && !this.sort.desc) {
          return [...value].reverse()
        }
        return field.name.split('->').reduce((item, field_segment) => item[field_segment], item)
      },
      expandRow(id) {
        this.expanded.push(id)
      },
      collapseRow(id) {
        this.expanded = this.expanded.filter(item => item !== id)
      },
      getDetails(item, field) {
        if (field.name === 'adapters') {
          return [...item['adapters']].reverse().map(adapter => [adapter])
        }
        return item[`${field.name}_details`]
      }
    }
  }
</script>

<style lang="scss">
  .x-striped-table {
    background: $theme-white;
    border-collapse: collapse;

    thead {
      tr {
        border-bottom: 2px dashed $grey-2;
      }
    }

    tbody {
      tr {
        td {
          vertical-align: top;
          line-height: 24px;
        }

        .svg-bg {
          fill: $theme-white;
        }
      }

      tr:nth-child(odd) {
        background: rgba($grey-1, 0.6);

        .svg-bg {
          fill: rgba($grey-1, 0.6);
        }
      }
    }

    .x-row {
      height: 30px;

      &.clickable:hover {
        cursor: pointer;
        box-shadow: 0 2px 16px -4px $grey-4;
      }

      .array {
        height: 24px;

        .md-chip {
          background-color: rgba($theme-orange, 0.2);
          height: 20px;
          line-height: 20px;
        }
      }

      .md-icon:hover {
        color: $theme-orange;
      }

      .details-container {
        overflow: hidden;
        margin: 0px -8px;

        .details {
          margin: 8px 0;
          padding: 8px;
          display: grid;
          grid-gap: 4px 0;
          background-color: rgba($grey-2, 0.6);
        }

        .slide-fade-enter-active {
          transition: all .6s cubic-bezier(1.0, 0.4, 0.8, 1.0);
        }

        .slide-fade-leave-active {
          transition: all .3s ease;
        }

        .slide-fade-enter, .slide-fade-leave-to {
          transform: translateY(-50%);
          opacity: 0;
        }
      }
    }
  }
</style>
