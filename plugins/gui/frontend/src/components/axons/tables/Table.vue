<template>
  <div class="x-table">
    <table class="table">
      <thead>
        <tr class="clickable">
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
          <th
            v-if="expandable"
            class="w-14"
          >
            <div>&nbsp;</div>
          </th>
          <x-table-head
            v-for="field in fields"
            :key="field.name"
            :field="field"
            :sort="sort"
            :sortable="onClickCol !== undefined"
            :filter="getFilter(field.name)"
            :filterable="filterable"
            @click="clickCol"
            @filter="(filter) => filterCol(field.name, filter)"
          />
        </tr>
      </thead>
      <tbody>
        <x-table-row
          v-for="row in data"
          :id="row[idField]"
          :key="row[idField]"
          :data="row"
          :fields="fields"
          :sort="sort"
          :filters="colFilters"
          :selected="value && value.includes(row[idField])"
          :expandable="expandable"
          :clickable="onClickRow !== undefined"
          :read-only="readOnly.includes(row[idField])"
          @input="(selected) => onSelect(row[idField], selected)"
          @click.native="() => clickRow(row[idField])"
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
</template>

<script>
  import xTableHead from './TableHead.vue'
  import xTableRow from './TableRow.vue'
  import xCheckbox from '../inputs/Checkbox.vue'

  export default {
    name: 'XTable',
    components: {
      xTableHead, xTableRow, xCheckbox
    },
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
      colFilters: {
        type: Object,
        default: undefined
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
      filterable: {
        type: Boolean,
        default: true
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
      },
      filterCol (fieldName, filter) {
        this.$emit('filter', {
          ...this.colFilters,
          [fieldName]: filter.toLowerCase()
        })
      },
      getFilter(fieldName) {
        if (!this.colFilters) {
          return undefined
        }
        return this.colFilters[fieldName] || ''
      }
    }
  }
</script>

<style lang="scss">
  .x-table {
    position: relative;
    height: calc(100% - 48px);
    overflow-y: auto;

    .table {
      border-collapse: collapse;

      thead {
        tr {
          th {
            position: sticky;
            top: 0;
            background: $theme-white;
            line-height: 28px;
            color: $theme-black;
            box-shadow: 8px 0 4px 0 $grey-2;
            z-index: 10;
          }
        }
      }
    }
  }

</style>
