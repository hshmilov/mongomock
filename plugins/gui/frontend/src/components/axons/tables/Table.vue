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
                  :alt="logo"
                  :title="logo"
                >{{ title }}<div
                  v-if="onClickCol"
                  :class="`sort ${sortClass(name)}`"
                />
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <x-table-row
            v-for="item in data"
            :id="item[idField]"
            :key="item[idField]"
            :data="item"
            :fields="dataFields"
            :sort="sort"
            :selected="value && value.includes(item[idField])"
            :expandable="expandable"
            :clickable="onClickRow !== undefined"
            :read-only="readOnly.includes(item[idField])"
            @input="(selected) => onSelect(item[idField], selected)"
            @click.native="() => clickRow(item[idField])"
          >
            <slot
              slot-scope="props"
              v-bind="props"
            />
          </x-table-row>
          <template v-if="pageSize">
            <tr
              v-for="n in pageSize - data.length"
              :key="n"
              class="x-table-row"
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
  import xTableRow from './TableRow.vue'

  export default {
    name: 'XTable',
    components: { xCheckbox, xTableRow },
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
        type: Array,
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
    computed: {
      ids () {
        return this.data.map(item => item[this.idField])
      },
      partSelected () {
        return Boolean(this.value && this.value.length && this.value.length < this.data.length)
      },
      allSelected () {
        return Boolean(this.value && this.value.length && this.value.length === this.data.length)
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
      onSelect (id, isSelected) {
        if (isSelected) {
          this.$emit('input', [...this.value, id])
        } else {
          this.$emit('input', this.value.filter(currentId => currentId !== id))
        }
      },
      onSelectAll (selected) {
        if (selected && (!this.value || !this.value.length)) {
          this.$emit('input', this.ids.filter(id => !this.readOnly.includes(id)))
        } else {
          this.$emit('input', [])
        }
        if (this.onClickAll) {
          this.onClickAll(selected)
        }
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
      width: max-content;
      min-width: 100%;
      border-top: 2px dashed $grey-2;
      overflow: hidden auto;
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
      }
    }
  }

</style>
