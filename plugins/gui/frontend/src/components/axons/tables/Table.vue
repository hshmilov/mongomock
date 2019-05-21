<template>
  <div class="x-table">
    <div class="header-container"></div>
    <div class="table-container">
      <table class="table">
        <thead>
          <tr class="clickable">
            <th
              v-if="value"
              class="w-14"
            >
              <div class="data-title">
                <x-checkbox
                  :data="allSelected"
                  :indeterminate="partSelected"
                  @change="onSelectAll"
                />
              </div>
            </th>
            <th v-if="expandable">
              <div class="data-title">&nbsp;</div>
            </th>
            <th
              v-for="{name, title, logo} in dataFields"
              :key="name"
              nowrap
              @click="clickCol(name)"
              @keyup.enter.stop="clickCol(name)"
            >{{ title }}
              <div
                class="data-title"
                :class="{sortable: onClickCol}"
              >
                <img
                  v-if="logo"
                  class="logo md-image"
                  :src="require(`Logos/adapters/${logo}.png`)"
                  height="20"
                  :alt="title"
                >{{ title }}<div
                  v-if="onClickCol"
                  :class="`sort ${sortClass(name)}`"
                />
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in data"
            :id="item[idField]"
            :key="item[idField]"
            class="x-row"
            :class="{
              clickable: onClickRow && !readOnly.includes(item[idField]),
              selected: selected.includes(item[idField])
            }"
            @click="clickRow(item[idField])"
            @mouseenter="enterRow(item[idField])"
            @mouseleave="leaveRow"
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
                class="active"
                @click.native.stop="collapseRow(item[idField])"
                >expand_less</md-icon>
              <md-icon
                v-else
                @click.native.stop="expandRow(item[idField])"
              >expand_more</md-icon>
            </td>
            <td
              v-for="schema in dataFields"
              :key="schema.name"
              nowrap
            >
              <slot
                :schema="schema"
                :data="item"
                :sort="sort"
                :hover-row="hovered === item[idField]"
                :expand-row="expanded.includes(item[idField])"
              >
                <x-table-data
                  :schema="schema"
                  :data="item"
                  :sort="sort"
                />
              </slot>
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
    </div>
  </div>
</template>

<script>
  import xCheckbox from '../inputs/Checkbox.vue'
  import xTableData from './TableData.vue'

  export default {
    name: 'XTable',
    components: { xCheckbox, xTableData },
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
        hovered: null,
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
      dataFields () {
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
        if (!document.getSelection().isCollapsed) return

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
      enterRow(id) {
        this.hovered = id
      },
      leaveRow() {
        this.hovered = null
      },
      expandRow(id) {
        this.expanded.push(id)
      },
      collapseRow(id) {
        this.expanded = this.expanded.filter(item => item !== id)
      }
    }
  }
</script>

<style lang="scss">
  .x-table {
    position: relative;
    height: calc(100% - 48px);
    padding-top: 30px;
    overflow: auto;

    .header-container {
      height: 30px;
      position: absolute;
      top: 0;
      right: 0;
      left: 0;
    }
    .table-container {
      height: 100%;
      overflow: auto;
      width: max-content;
      min-width: 100%;
      border-top: 2px dashed $grey-2;
      .table {
        background: $theme-white;
        border-collapse: collapse;

        thead {
          th {
            color: transparent;
            height: 0;
            line-height: 0;

            .data-title {
              position: absolute;
              color: $theme-black;
              top: 0;
              line-height: 28px;
              &.sortable {
                cursor: pointer;
              }
            }
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

          .x-data {
            display: flex;
          }

          &.clickable:hover {
            cursor: pointer;
            box-shadow: 0 2px 16px -4px $grey-4;
          }

          &.selected {
            background-color: rgba($theme-blue, 0.2);
          }

          .array {
            min-height: 24px;
          }

          .md-icon {
            width: 14px;
            min-width: 14px;
            &:hover, &.active {
              color: $theme-orange;
            }
          }

        }
      }
    }
  }

</style>
