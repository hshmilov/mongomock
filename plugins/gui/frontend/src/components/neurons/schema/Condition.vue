<template>
  <div class="x-condition">
    <x-select-typed-field
      v-if="!parentField"
      :id="fieldId"
      :value="field"
      :filtered-adapters="condition.filteredAdapters"
      :options="schema"
      @input="onChangeFieldType"
    />
    <x-select
      v-else
      :value="field"
      :options="schema"
      :searchable="true"
      class="field-select field-select__indented"
      @input="onChangeFieldType"
    />
    <x-select
      v-if="!isParent && opsList.length"
      :id="opId"
      v-model="compOp"
      :options="opsList"
      placeholder="func..."
      class="expression-comp"
    />
    <component
      :is="valueSchema.type"
      v-if="showValue"
      :id="valueId"
      v-model="value"
      :schema="valueSchema"
      class="expression-value"
      :class="{'grid-span2': !opsList.length}"
      :clearable="false"
    />
    <div v-else />
  </div>
</template>

<script>
  import xSelect from '../../axons/inputs/select/Select.vue'
  import xSelectTypedField from '../inputs/SelectTypedField.vue'
  import string from './types/string/StringEdit.vue'
  import number from './types/numerical/NumberEdit.vue'
  import integer from './types/numerical/IntegerEdit.vue'
  import bool from './types/boolean/BooleanEdit.vue'
  import array from './types/numerical/IntegerEdit.vue'

  import { mapState, mapGetters } from 'vuex'
  import { GET_MODULE_SCHEMA, GET_DATA_SCHEMA_BY_NAME } from '../../../store/getters'
  import {checkShowValue, getOpsList, getOpsMap, getValueSchema, schemaEnumFind} from '../../../logic/condition'

  import _isEqual from 'lodash/isEqual'

  export default {
    name: 'XCondition',
    components: {
      xSelect, xSelectTypedField, string, number, integer, bool, array
    },
    model: {
      prop: 'condition',
      event: 'input'
    },
    props: {
      module: {
        type: String,
        required: true
      },
      condition: {
        type: Object,
        default: undefined
      },
      isParent: {
        type: Boolean,
        default: false
      },
      parentField: {
        type: String,
        default: ''
      },
      first: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
      }
    },
    computed: {
      ...mapState({
        savedViews (state) {
          return state[this.module].views.saved.content.data
        },
        isUniqueAdapters(state) {
          return state[this.module].view.query.meta && state[this.module].view.query.meta.uniqueAdapters
        }
      }),
      ...mapGetters({
        getModuleSchema: GET_MODULE_SCHEMA, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME
      }),
      field () {
        return this.condition.field
      },
      compOp: {
        get () {
          return this.condition.compOp
        },
        set (compOp) {
          let value = this.value
          // Reset the value if the value schema is about to change
          if(!_isEqual(getValueSchema(this.fieldSchema, compOp), this.valueSchema)) {
            value = ''
          }
          this.updateCondition({ compOp, value })
        }
      },
      value: {
        get () {
          return this.condition.value
        },
        set (value) {
          this.updateCondition({ value })
        }
      },
      schema () {
        if (this.isParent) {
          return this.schemaObject
        }
        if (this.parentField) {
          const parentSchema = this.schemaByName[this.parentField]
          return Array.isArray(parentSchema.items)? parentSchema.items : parentSchema.items.items
        }
        return this.schemaFlat
      },
      schemaFlat () {
        let schema = this.getModuleSchema(this.module)
        if (!schema || !schema.length) return []
        /* Compose a schema by which to offer fields and values for building query expressions in the wizard */
        schema[0].fields = [{
          name: 'saved_query', title: 'Saved Query', type: 'string', format: 'predefined',
          enum: this.savedViews.map((view) => {
            return {
              name: view.view.query.filter, title: view.name
            }
          })
        }, ...schema[0].fields]
        return this.addFilteredOption(schema)
      },
      schemaObject () {
        return this.addFilteredOption(this.getModuleSchema(this.module, true))
      },
      schemaByName () {
        return this.schemaObject.reduce((map, item) => {
          item.fields.forEach(field => map[field.name] = field)
          return map
        }, this.getDataSchemaByName(this.module))
      },
      fieldSchema () {
        if (!this.field) return {}
        if (this.parentField) {
          return this.schemaByName[`${this.parentField}.${this.field}`]
        }
        if (this.field === 'saved_query') {
          return this.schemaFlat[0].fields[0]
        }
        return this.schemaByName[this.field]
      },
      valueSchema () {
        return getValueSchema(this.fieldSchema, this.compOp)
      },
      opsMap () {
          return getOpsMap(this.fieldSchema)
      },
      opsList () {
          return getOpsList(this.opsMap)
      },
      showValue () {
        return checkShowValue(this.fieldSchema, this.compOp)
      },
      fieldId() {
        return this.first ? 'query_field' : undefined
      },
      opId() {
        return this.first ? 'query_op' : undefined
      },
      valueId() {
        return this.first ? 'query_value' : undefined
      }
    },
    watch: {
      isUniqueAdapters() {
        this.updateCondition()
      },
      field () {
        if (!Object.keys(this.opsMap).includes(this.compOp)) {
          this.compOp = ''
        }
        if (this.field.endsWith('.id')) {
          this.compOp = 'exists'
        }
      },
      valueSchema (newSchema, oldSchema) {
        if (!this.value) {
          return
        }
        if (!newSchema || !oldSchema || this.isParent) return
        if (!oldSchema.type && !oldSchema.format) return
        if (newSchema.type !== oldSchema.type || newSchema.format !== oldSchema.format) {
          this.value = null
        }
        if (newSchema.enum && !schemaEnumFind(newSchema, this.value) && newSchema.enum.length > 0) {
          this.value = null
        }
      }
    },
    methods: {
      updateCondition (update) {
        this.$emit('input', { ...this.condition, ...update })
      },
      onChangeFieldType(field, fieldType, filteredAdapters){
        this.updateCondition({ field, fieldType, filteredAdapters })
      },
      addFilteredOption(schema){
          if(schema && schema.length > 0 && schema[0].name === 'axonius'){
              schema[0].plugins = this.getModuleSchema(this.module).
              filter(adapter => adapter.name !== 'axonius').
              map(adapter => {
                  return {title: adapter.title, name: adapter.name}
              })
          }
          return schema
      }
    }
  }
</script>

<style lang="scss">
    .x-condition {
        display: grid;
        grid-template-columns: 240px 80px auto;
        justify-items: stretch;
        align-items: center;
        grid-gap: 8px;

        .expression-value {
            width: auto;
            min-width: 0;
        }

        .field-select__indented {
          margin-left: 60px;
        }
    }
</style>
