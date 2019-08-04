<template>
  <div class="x-condition">
    <x-select-typed-field
      :id="first? 'query_field': undefined"
      v-model="condition.field"
      :options="schema"
    />
    <x-select
      v-if="!isParent && opsList.length"
      :id="first? 'query_op': undefined"
      v-model="condition.compOp"
      :options="opsList"
      placeholder="func..."
      class="expression-comp"
    />
    <component
      :is="valueSchema.type"
      v-if="showValue"
      :id="first? 'query_value': undefined"
      v-model="condition.value"
      :schema="valueSchema"
      class="expression-value"
      :class="{'grid-span2': !opsList.length}"
      :clearable="false"
    />
    <div v-else />
  </div>
</template>

<script>
  import xSelect from '../../axons/inputs/Select.vue'
  import xSelectTypedField from '../inputs/SelectTypedField.vue'
  import string from './types/string/StringEdit.vue'
  import number from './types/numerical/NumberEdit.vue'
  import integer from './types/numerical/IntegerEdit.vue'
  import bool from './types/boolean/BooleanEdit.vue'
  import array from './types/numerical/IntegerEdit.vue'

  import { compOps } from '../../../constants/filter'
  import IP from 'ip'
  import { mapState, mapGetters } from 'vuex'
  import { GET_DATA_FIELDS_BY_PLUGIN, GET_DATA_SCHEMA_BY_NAME } from '../../../store/getters'

  export default {
    name: 'XCondition',
    components: {
      xSelect, xSelectTypedField, string, number, integer, bool, array
    },
    props: {
      module: {
        type: String,
        required: true
      },
      value: {
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
        condition: { ...this.value },
        processedValue: ''
      }
    },
    computed: {
      ...mapState({
        savedViews (state) {
          return state[this.module].views.saved.content.data
        }
      }),
      ...mapGetters({
        getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME
      }),
      conditionField () {
        return this.condition.field
      },
      schema () {
        if (this.isParent) {
          return this.schemaObject
        }
        if (this.parentField) {
          return this.schemaByName[this.parentField].items
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
        return schema
      },
      schemaObject () {
        return this.getDataFieldsByPlugin(this.module, true)
      },
      schemaByName () {
        return this.schemaObject.reduce((map, item) => {
          item.fields.forEach(field => map[field.name] = field)
          return map
        }, this.getDataSchemaByName(this.module))
      },
      fieldSchema () {
        if (!this.condition.field) return {}
        if (this.parentField) {
          return this.schemaByName[`${this.parentField}.${this.condition.field}`]
        }
        if (this.condition.field === 'saved_query') {
          return this.schemaFlat[0].fields[0]
        }
        return this.schemaByName[this.condition.field]
      },
      valueSchema () {
        if (this.fieldSchema && this.fieldSchema.type === 'array'
          && ['contains', 'equals', 'subnet', 'notInSubnet'].includes(this.condition.compOp)) {
          return this.fieldSchema.items
        }
        if (this.fieldSchema && this.fieldSchema.format && this.fieldSchema.format === 'date-time'
          && ['days'].includes(this.condition.compOp)) {
          return { type: 'integer' }
        }
        return this.fieldSchema
      },
      opsMap () {
        if (!this.fieldSchema || !this.fieldSchema.type) return {}
        let ops = {}
        let schema = this.fieldSchema
        if (schema.type === 'array') {
          ops = compOps[`array_${schema.format}`] || compOps['array']
          schema = schema.items
        }
        if (schema.enum && schema.format !== 'predefined') {
          ops = { ...ops, equals: compOps[schema.type].equals, exists: compOps[schema.type].exists }
        } else if (schema.format) {
          ops = { ...ops, ...compOps[schema.format] }
        } else {
          ops = { ...ops, ...compOps[schema.type] }
        }
        if (schema.type === 'array' && ops.exists) {
          ops.exists = `(${ops.exists} and {field} != [])`
        }
        if (this.valueSchema.name === 'labels') {
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
            title: this.opTitleTranslation[op] ? this.opTitleTranslation[op] : op
          }
        })
      },
      showValue () {
        return this.checkShowValue(this.condition.compOp)
      }
    },
    watch: {
      isParent () {
        this.condition.field = ''
        this.condition.compOp = ''
        this.condition.value = null
        this.$emit('error', '')
      },
      value (newValue) {
        if (newValue.field !== this.condition.field) {
          this.condition = { ...newValue }
        }
      },
      conditionField () {
        if (this.condition.field.includes('.id')) {
          this.condition.compOp = 'exists'
        }
      },
      valueSchema (newSchema, oldSchema) {
        if (!newSchema || !oldSchema || this.isParent) return
        if (!oldSchema.type && !oldSchema.format) return
        if (newSchema.type !== oldSchema.type || newSchema.format !== oldSchema.format) {
          this.condition.value = null
        }
      }
    },
    updated () {
      this.compileCondition()
    },
    created () {
      if (this.condition.field) {
        this.compileCondition()
      }
    },
    methods: {
      checkShowValue (op) {
        return this.fieldSchema && (this.fieldSchema.format === 'predefined' ||
          (op && this.opsList.length && this.opsMap[op] && this.opsMap[op].includes('{val}')))
      },
      checkErrors () {
        if (this.opsList.length && (!this.condition.compOp || !this.opsMap[this.condition.compOp])) {
          this.condition.compOp = ''
          return 'Comparison operator is needed to add expression to the filter'
        } else if (this.showValue && (typeof this.condition.value !== 'number' || isNaN(this.condition.value))
          && (!this.condition.value || !this.condition.value.length)) {
          return 'A value to compare is needed to add expression to the filter'
        } else {
          return ''
        }
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
        let subnets = this.condition.value.split(',')
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
        rawIpsArray = rawIpsArray.sort((range1, range2) => {return range1[0] - range2[0]})
        rawIpsArray.forEach(range => {
          let lastRange = result.pop(-1)
          let new1 = [lastRange[0], range[0]]
          let new2 = [range[1], lastRange[1]]
          result.push(new1)
          result.push(new2)
        })
        result = result.map(range => {return `${this.condition.field}_raw == match({"$gte": ${range[0]}, "$lte": ${range[1]}})`}).join(' or ')
        result = `(${result})`
        this.processedValue = result
        return ''
      },
      formatInSubnet () {
        let subnet = this.condition.value
        let rawIps = this.convertSubnetToRaw(subnet)

        if (rawIps.length == 0) {
          return 'Specify <address>/<CIDR> to filter IP by subnet'
        }
        this.processedValue = rawIps
        return ''
      },
      formatVersion () {
        let version = this.condition.value
        let rawVersion =  this.convertVersionToRaw(version)
        if (rawVersion.length == 0) {
          return 'Invalid version format, must be <optional>:<period>.<separated>.<numbers>'
        }
        this.processedValue = "'" + rawVersion + "'"
        return ''
      },
      formatCondition () {
        this.processedValue = ''
        if (this.fieldSchema.format && this.fieldSchema.format === 'ip') {
          if (this.condition.compOp === 'subnet') {
            return this.formatInSubnet()
          }
          if (this.condition.compOp === 'notInSubnet') {
            return this.formatNotInSubnet()
          }
        }
        if (this.fieldSchema.format && this.fieldSchema.format === 'version') {
          if (this.condition.compOp === 'earlier than' || this.condition.compOp === 'later than') {
            return this.formatVersion()
          }
        }
        if (this.fieldSchema.enum && this.fieldSchema.enum.length && this.condition.value) {
          let exists = this.fieldSchema.enum.filter((item) => {
            return (item.name) ? (item.name === this.condition.value) : item === this.condition.value
          })
          if (!exists || !exists.length) return 'Specify a valid value for enum field'
        }
        return ''
      },
      composeCondition () {
        let cond = '({val})'
        if (this.opsMap[this.condition.compOp]) {
          cond = this.opsMap[this.condition.compOp].replace(/{field}/g, this.condition.field)
        } else if (this.opsList.length) {
          this.condition.compOp = ''
          this.condition.value = ''
          return ''
        }

        let val = this.processedValue ? this.processedValue : this.condition.value
        let iVal = Array.isArray(val) ? -1 : undefined
        return cond.replace(/{val}/g, () => {
          if (iVal === undefined) return val
          iVal = (iVal + 1) % val.length
          return val[iVal]
        })
      },
      compileCondition () {
        this.$emit('input', this.condition)
        if (!this.condition.field || this.isParent) return

        let error = this.checkErrors() || this.formatCondition()
        this.$emit('error', error)
        if (error) {
          return
        }
        this.$emit('change', this.composeCondition())
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
    }
</style>
