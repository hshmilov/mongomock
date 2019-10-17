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
    <template v-if="isFieldFilterable">
      <label>Filter by</label>
      <x-search-input
        v-model="valueFilter"
        class="grid-span2"
      />
    </template>
    <x-checkbox
      v-model="includeEmpty"
      :read-only="Boolean(valueFilter)"
      label="Include entities with no value"
      class="grid-span2"
    />
  </div>
</template>

<script>
  import xSelect from '../../../axons/inputs/Select.vue'
  import xSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue'
  import xSelectTypedField from '../../../neurons/inputs/SelectTypedField.vue'
  import xSearchInput from '../../../neurons/inputs/SearchInput.vue'
  import xCheckbox from '../../../axons/inputs/Checkbox.vue'
  import chartMixin from './chart'
  import {isObjectListField} from '../../../../constants/utils'

  import { mapGetters } from 'vuex'
  import { GET_DATA_FIELDS_BY_PLUGIN, GET_DATA_SCHEMA_BY_NAME } from '../../../../store/getters'

  export default {
    name: 'XChartSegment',
    components: {
      xSelect, xSelectSymbol, xSelectTypedField, xSearchInput, xCheckbox
    },
    mixins: [chartMixin],
    computed: {
      ...mapGetters({
        getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME
      }),
      initConfig () {
        return  {
          entity: '', view: '', field: {
            name: ''
          }
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
          this.config = { ...this.config,
            field: this.schemaByName[fieldName] || { name: '' }
          }
        }
      },
      valueFilter: {
        get () {
          return this.config['value_filter']
        },
        set (filter) {
          this.config = { ...this.config,
            'value_filter': filter,
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
        return this.getDataFieldsByPlugin(this.entity).map(category => {
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
      schemaByName () {
        if (!this.entity) return {}
        return this.getDataSchemaByName(this.entity)
      },
      isFieldFilterable () {
        return this.config.field.type === 'string' && !this.config.field.format
      }
    },
    methods: {
      validate () {
        this.$emit('validate', this.fieldName)
      },
      updateEntity(entity) {
        if (entity === this.entity) return
        this.config = {
          entity,
          view: '',
          field: {
            name: ''
          }
        }
      }
    }
  }
</script>

<style lang="scss">

</style>
