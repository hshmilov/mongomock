<template>
  <div class="x-chart-metric">
    <x-select-symbol
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      @input="updateEntity"
    />
    <x-select
      v-model="view"
      :options="views[entity]"
      :searchable="true"
      placeholder="query (or empty for all)"
      class="view-name grid-span2"
    />
    <label>Segment by</label>
    <x-select-typed-field
      v-model="fieldName"
      :options="fieldOptions"
      class="grid-span2"
    />
    <template>
      <label class="filter-by-label">Filter by</label>
      <x-filter-contains
        v-model="filters"
        class="grid-span2"
        :options="filterFields"
        :min="1"
      />
    </template>
    <x-checkbox
      v-model="includeEmpty"
      :read-only="isAllowIncludeEmpty"
      label="Include entities with no value"
      class="grid-span2"
    />
  </div>
</template>

<script>
  import xSelect from '../../../axons/inputs/select/Select.vue'
  import xSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue'
  import xSelectTypedField from '../../../neurons/inputs/SelectTypedField.vue'
  import XFilterContains from '../../../neurons/schema/FilterContains.vue'
  import xCheckbox from '../../../axons/inputs/Checkbox.vue'
  import chartMixin from './chart'
  import {getParentFromField, isObjectListField} from '../../../../constants/utils'

  import { mapGetters } from 'vuex'
  import { GET_MODULE_SCHEMA, GET_DATA_SCHEMA_BY_NAME } from '../../../../store/getters'

  export default {
    name: 'XChartSegment',
    components: {
      xSelect, xSelectSymbol, xSelectTypedField, xCheckbox, XFilterContains
    },
    mixins: [chartMixin],
    computed: {
      ...mapGetters({
        getModuleSchema: GET_MODULE_SCHEMA, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME
      }),
      initConfig () {
        return  {
          entity: '', view: '', field: {name: ''}, filters: [{name : '', value: ''}]
        }
      },
      entity: {
        get () {
          return this.config.entity
        },
        set (entity) {
          this.config = { ...this.config, entity }
        }
      },
      view: {
        get () {
          return this.config.view
        },
        set (view) {
          this.config = { ...this.config, view }
        }
      },
      fieldName: {
        get () {
          return this.config.field.name
        },
        set (fieldName) {
          if (fieldName === this.config.field.name) {
            return
          }
          const field = this.schemaByName[fieldName] || { name: '' }
          this.config = { ...this.config,
            field,
            'value_filter':[{name: '', value: ''}]
          }
        }
      },
      filters: {
        get () {
          if (Array.isArray(this.config['value_filter'])) {
            return this.config['value_filter']
          }
          return [{'name': this.config.field.name, 'value': this.config['value_filter']}]
        },
        set (filters) {
          this.config = { ...this.config,
            'value_filter': filters,
            'include_empty': false
          }
        }
      },
      includeEmpty: {
        get () {
          return this.config['include_empty']
        },
        set (includeEmpty) {
          this.config = { ...this.config, 'include_empty': includeEmpty }
        }
      },
      fieldOptions () {
        if (!this.entity) return []
        return this.getModuleSchema(this.entity).map(category => {
          return {
            ...category,
            fields: category.fields.filter(field => {
              if (!field.name.startsWith('specific_data') && !field.name.startsWith('adapters_data')) {
                return false
              }
              return !isObjectListField(field)
            })
          }
        })
      },
      filterFields () {
        if (this.fieldName === '') {
          return []
        }
        const parentName = getParentFromField(this.fieldName)
        const parentSchema = this.schemaByName[parentName]
        const isComplexObject = parentSchema && isObjectListField(parentSchema)
        if (!isComplexObject) {
          return [this.config.field]
        }

        const availableFields =  Array.isArray(parentSchema.items)? parentSchema.items : parentSchema.items.items
        return availableFields.filter(this.isFieldFilterable).map((option) => {
          return {
            ...option,
            name: parentName + '.' + option.name
          }
        })
      },
      schemaByName () {
        if (!this.entity) return {}
        return this.getDataSchemaByName(this.entity)
      },
      isAllowIncludeEmpty () {
        return !!this.filters.filter((item) => item.name && item.value ).length
      },
      isFiltersValid() {
        return !this.filters.find(item => !!item.name !== !!item.value)
      }
    },
    methods: {
      validate () {
        this.$emit('validate', this.fieldName && this.isFiltersValid)
      },
      updateEntity(entity) {
        if (entity === this.entity) return
        this.config = {
          entity,
          view: '',
          field: {
            name: ''
          },
          'value_filter': [{name : '', value: ''}]
        }
      },
      isFieldFilterable (field) {
        const isFieldChildOfComplexObject = field.branched
        const isFieldNotDateOrArrayOfDates = field.format !== 'date-time'
                                          && ( !field.items || field.items.format !== 'date-time' )
        return !isFieldChildOfComplexObject && isFieldNotDateOrArrayOfDates && !isObjectListField(field)
      }
    }
  }
</script>

<style lang="scss">
  .x-chart-metric {
    .filter-by-label {
      align-self: flex-start;
      margin-top: 14px;
    }
  }
</style>
