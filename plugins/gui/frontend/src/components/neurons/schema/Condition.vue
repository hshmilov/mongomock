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

  import { compOps } from '../../../constants/filter'
  import { pluginMeta } from '../../../constants/plugin_meta'
  import IP from 'ip'
  import { mapState, mapGetters } from 'vuex'
  import { GET_DATA_FIELDS_BY_PLUGIN, GET_DATA_SCHEMA_BY_NAME } from '../../../store/getters'
  import { getExcludedAdaptersFilter } from '../../../constants/utils'
  import { INCLUDE_OUDATED_MAGIC, AGGREGATED_FIELDS_CONVERTER } from '../../../constants/filter'

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
        processedValue: ''
      }
    },
    computed: {
      ...mapState({
        savedViews (state) {
          return state[this.module].views.saved.content.data
        },
        isUniqueAdapters(state) {
          return state[this.module].view.query.filter.includes(INCLUDE_OUDATED_MAGIC)
        }
      }),
      ...mapGetters({
        getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME
      }),
      field () {
        return this.condition.field
      },
      compOp: {
        get () {
          return this.condition.compOp
        },
        set (compOp) {
          this.updateCondition({ compOp })
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
      error () {
        if (!this.field) {
          return ''
        }
        if (this.opsList.length && (!this.compOp || !this.opsMap[this.compOp])) {
          return 'Comparison operator is needed to add expression to the filter'
        } else if (this.showValue && (typeof this.value !== 'number' || isNaN(this.value))
                && (!this.value || !this.value.length)) {
          return 'A value to compare is needed to add expression to the filter'
        }
        return ''
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
        let schema = this.getDataFieldsByPlugin(this.module)
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
        return this.addFilteredOption(this.getDataFieldsByPlugin(this.module, true))
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
        if (this.fieldSchema && ['integer', 'number', 'array'].includes(this.fieldSchema.type) && (this.compOp === 'IN' || this.compOp ==='contains')) {
            return { type: 'string' }
        }
        if (this.fieldSchema && this.fieldSchema.type === 'array'
          && ['contains', 'equals', 'subnet', 'notInSubnet', 'starts', 'ends'].includes(this.compOp)) {
          return this.fieldSchema.items
        }
        if (this.fieldSchema && this.fieldSchema.format && this.fieldSchema.format === 'date-time'
          && ['days'].includes(this.compOp)) {
          return { type: 'integer' }
        }
        let newSchema = this.fieldSchema
        if(this.compOp === 'IN' && this.fieldSchema.enum){
            newSchema = { ...newSchema, enum: undefined }
        }
        return newSchema
      },
      opsMap () {
        if (!this.fieldSchema || !this.fieldSchema.type) return {}
        let ops = {}
        let schema = this.fieldSchema
        if (schema.type === 'array') {
          ops = compOps[`array_${schema.format}`] || compOps['array']
          schema = schema.items
        }
        if (schema.enum && schema.format !== 'predefined' && schema.format !== 'tag') {
          ops = {
              ...ops,
              equals: compOps[schema.type].equals,
              exists: compOps[schema.type].exists,
              IN: compOps[schema.type].IN
          }
        }
        else if (schema.format) {
              ops = { ...ops, ...compOps[schema.format] }
        } else {
          ops = { ...ops, ...compOps[schema.type] }
        }
        if (schema.type === 'array' && ops.exists) {
          ops.exists = `(${ops.exists} and {field} != [])`
        }
        if (this.fieldSchema.name === 'labels') {
          delete ops.size
        }
        return ops
      },
      opTitleTranslation () {
        return {
          count_equals: 'count =',
          count_below: 'count <',
          count_above: 'count >',
          notInSubnet: 'not in subnet',
          subnet: 'in subnet'
        }
      },
      opsList () {
        return Object.keys(this.opsMap).map((op) => {
          return {
            name: op,
            title: this.opTitleTranslation[op] ? this.opTitleTranslation[op].toLowerCase() : op.toLowerCase()
          }
        })
      },
      showValue () {
        return this.checkShowValue(this.compOp)
      },
      pluginsMeta () {
          return Object.keys(pluginMeta).reduce((map, obj) => {
              map[pluginMeta[obj].title] = obj
              return map
          }, {})
      },
      isFieldTypeFiltered () {
        return this.condition.filteredAdapters
                && !this.condition.filteredAdapters.selectAll
                && !this.condition.filteredAdapters.clearAll
      },
      // Substitutes fields to aggregated fields if they exist.
      aggregatedField() {
        const field = this.field
        const compOp = this.compOp
        // Check whether outdated adapter was toggled in the Wizard
        if (this.isUniqueAdapters || this.isFieldTypeFiltered) {
          return field
        }
        // only compare operators of fields that are found in aggregated fields map and include the comperator operator
        const aggDef = AGGREGATED_FIELDS_CONVERTER.find(item => item.path == field)
        if (aggDef === undefined) {
          return field
        }
        const aggOps = aggDef.validOps
        if (!aggOps.includes(compOp)) {
          return field
        }
        return aggDef.aggregatedName
      },
      fieldId () {
        return this.first ? 'query_field' : undefined
      },
      opId () {
        return this.first ? 'query_op' : undefined
      },
      valueId () {
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
        if (newSchema.enum && !this.schemaEnumFind(newSchema) && newSchema.enum.length > 0) {
          this.value = null
        }
      }
    },
    methods: {
      updateCondition (update) {
        this.$emit('input', { ...this.condition, ...update })
        this.$nextTick(this.compileCondition)
      },
      schemaEnumFind (schema) {
        return schema.enum.find((item, index) => {
          if(schema.type === 'integer' && isNaN(item)) {
            return index+1 === this.value 
          }
          else {
            return (item.name || item) === this.value
          }
        })
      },
      checkShowValue (op) {
        return this.fieldSchema && (this.fieldSchema.format === 'predefined' ||
          (op && this.opsList.length && this.opsMap[op] && this.opsMap[op].includes('{val}')))
      },
      extendVersionField (val) {
        let extended = ''
        for (var i = 0; i < 8 - val.length; i ++) {
          extended = '0' + extended
        }
        extended = extended + val
        return extended
      },
      convertVersionToRaw (version) {
        try {
          let converted = '0'
          if (version.includes(':')) {
            if (version.includes('.') && version.indexOf(':') > version.indexOf('.')) {
              return ''
            }
            let epoch_split = version.split(':')
            converted = epoch_split[0]
            version = epoch_split[1]
          }
          let split_version = [version]
          if (version.includes('.')) {
            split_version = version.split('.')
          }
          for (var i = 0; i < split_version.length; i ++) {
            if (isNaN(split_version[i])) {
              return ''
            }
            if (split_version[i].length > 8) {
              split_version[i] = split_version[i].substring(0,9)
            }
            let extended = this.extendVersionField(split_version[i])
            converted = converted + extended
          }
          return converted
        } catch (err) {
          return ''
        }
      },
      convertSubnetToRaw (val) {
        if (!val.includes('/') || val.indexOf('/') === val.length - 1) {
          return []
        }
        try {
          let subnetInfo = IP.cidrSubnet(val)
          return [IP.toLong(subnetInfo.networkAddress), IP.toLong(subnetInfo.broadcastAddress)]
        } catch (err) {
          return []
        }
        return []
      },
      formatNotInSubnet () {
        let subnets = this.value.split(',')
        let rawIpsArray = []
        let result = [[0, 0xffffffff]]
        for (var i = 0; i < subnets.length; i++) {
          let subnet = subnets[i].trim()
          if (subnet === '') {
            continue
          }
          let rawIps = this.convertSubnetToRaw(subnet)
          if (rawIps.length == 0) {
            return `Invalid "${subnet}", Specify <address>/<CIDR>`
          }
          rawIpsArray.push(rawIps)

        }
        rawIpsArray.sort((range1, range2) => {return range1[0] - range2[0]})
        rawIpsArray.forEach(range => {
          let lastRange = result.pop(-1)
          let new1 = [lastRange[0], range[0]]
          let new2 = [range[1], lastRange[1]]
          result.push(new1)
          result.push(new2)
        })
        result = result.map(range => {return `${this.field}_raw == match({"$gte": ${range[0]}, "$lte": ${range[1]}})`}).join(' or ')
        result = `(${result})`
        this.processedValue = result
        return ''
      },
      formatInSubnet () {
        let subnet = this.value
        let rawIps = this.convertSubnetToRaw(subnet)

        if (rawIps.length == 0) {
          return 'Specify <address>/<CIDR> to filter IP by subnet'
        }
        this.processedValue = rawIps
        return ''
      },
      formatVersion () {
        let version = this.value
        let rawVersion =  this.convertVersionToRaw(version)
        if (rawVersion.length == 0) {
          return 'Invalid version format, must be <optional>:<period>.<separated>.<numbers>'
        }
        this.processedValue = "'" + rawVersion + "'"
        return ''
      },
      formatIn(){
          let values = this.value.match(/(\\,|[^,])+/g)
          if(this.fieldSchema.name === 'adapters'){
              values = values.map(value => {
                  return this.pluginsMeta[value.trim()]
              }).filter(value => value != null)
          }
          if(['integer', 'number'].includes(this.fieldSchema.type)){
              this.processedValue = values.map(value => parseFloat(value)).filter(value => !isNaN(value)).join(',')
          } else {
              this.processedValue = '"' + values.join('","') + '"'
          }
          this.processedValue = this.processedValue.replace('\\\\,',',')
          return ''
      },
      formatCondition () {
        this.processedValue = ''
        if(this.compOp === 'IN'){
          return this.formatIn()
        }
        if (this.fieldSchema.format && this.fieldSchema.format === 'ip') {
          if (this.compOp === 'subnet') {
            return this.formatInSubnet()
          }
          if (this.compOp === 'notInSubnet') {
            return this.formatNotInSubnet()
          }
        }

        if (this.fieldSchema.format && this.fieldSchema.format === 'version') {
          if (this.compOp === 'earlier than' || this.compOp === 'later than') {
            return this.formatVersion()
          }
        }
        if (this.fieldSchema.enum && this.fieldSchema.enum.length && this.value) {
          if (!this.schemaEnumFind(this.fieldSchema)) {
            return 'Specify a valid value for enum field'
          }
        }
        return ''
      },
      composeCondition () {
        return `(${getExcludedAdaptersFilter(this.condition.fieldType, this.condition.field,
                this.condition.filteredAdapters, this.getConditionExpression())})`
      },
      getConditionExpression () {
        let cond = '({val})'
        if (this.opsMap[this.compOp]) {
          cond = this.opsMap[this.compOp].replace(/{field}/g, this.aggregatedField)
        } else if (this.opsList.length) {
          this.compOp = ''
          this.value = ''
          return ''
        }

        let val = this.processedValue ? this.processedValue : this.value
        let iVal = Array.isArray(val) ? -1 : undefined
        return cond.replace(/{val}/g, () => {
          if (iVal === undefined) return val
          iVal = (iVal + 1) % val.length
          return val[iVal]
        })
      },
      compileCondition () {
        if (!this.field) return
        if (this.isParent) {
            this.$emit('change')
            return
        }
        let error = this.error || this.formatCondition()
        if (error) {
          this.$emit('error', error)
          return
        }
        this.$emit('change', this.composeCondition())
      },
      onChangeFieldType(field, fieldType, filteredAdapters){
        this.updateCondition({ field, fieldType, filteredAdapters })
      },
      addFilteredOption(schema){
          if(schema && schema.length > 0 && schema[0].name === 'axonius'){
              schema[0].plugins = this.getDataFieldsByPlugin(this.module).
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
