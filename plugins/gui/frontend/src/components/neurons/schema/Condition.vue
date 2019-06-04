<template>
    <div class="x-condition">
        <x-select-typed-field :options="schema" v-model="condition.field" :id="first? 'query_field': undefined"/>
        <x-select v-if="!isParent && opsList.length" :options="opsList" v-model="condition.compOp"
                  placeholder="func..." :id="first? 'query_op': undefined" class="expression-comp"/>
        <component v-if="showValue" :is="valueSchema.type" :schema="valueSchema" v-model="condition.value"
                   class="expression-value" :class="{'grid-span2': !opsList.length}" :clearable="false"
                   :id="first? 'query_value': undefined"/>
        <div v-else></div>
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

    import {compOps} from '../../../constants/filter'
    import IP from 'ip'
    import {mapState, mapGetters} from 'vuex'
    import {GET_DATA_FIELDS_BY_PLUGIN, GET_DATA_SCHEMA_BY_NAME} from '../../../store/getters'

    export default {
        name: 'x-condition',
        components: {
            xSelect, xSelectTypedField, string, number, integer, bool, array
        },
        props: {
            module: {required: true}, value: {}, isParent: {}, parentField: {}, first: {default: false}
        },
        computed: {
            ...mapState({
                savedViews(state) {
                    return state[this.module].views.saved.data
                }
            }),
            ...mapGetters({
                getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME
            }),
            conditionField() {
                return this.condition.field
            },
            schema() {
                if (this.isParent) {
                    return this.schemaObject
                }
                if (this.parentField) {
                    return this.schemaByName[this.parentField].items
                }
                return this.schemaFlat
            },
            schemaFlat() {
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
            schemaObject() {
                return this.getDataFieldsByPlugin(this.module, true)
            },
            schemaByName() {
                return this.schemaObject.reduce((map, item) => {
                    item.fields.forEach(field => map[field.name] = field)
                    return map
                }, this.getDataSchemaByName(this.module))
            },
            fieldSchema() {
                if (!this.condition.field) return {}
                if (this.parentField) {
                    return this.schemaByName[`${this.parentField}.${this.condition.field}`]
                }
                if (this.condition.field === 'saved_query') {
                    return this.schemaFlat[0].fields[0]
                }
                return this.schemaByName[this.condition.field]
            },
            valueSchema() {
                if (this.fieldSchema && this.fieldSchema.type === 'array'
                    && ['contains', 'equals', 'subnet', 'notInSubnet'].includes(this.condition.compOp)) {
                    return this.fieldSchema.items
                }
                if (this.fieldSchema && this.fieldSchema.format && this.fieldSchema.format === 'date-time'
                    && ['days'].includes(this.condition.compOp)) {
                    return {type: 'integer'}
                }
                return this.fieldSchema
            },
            opsMap() {
                if (!this.fieldSchema || !this.fieldSchema.type) return {}
                let ops = {}
                let schema = this.fieldSchema
                if (schema.type === 'array') {
                    ops = compOps[`array_${schema.format}`] || compOps['array']
                    schema = schema.items
                }
                if (schema.enum && schema.format !== 'predefined') {
                    ops = {...ops, equals: compOps[schema.type].equals, exists: compOps[schema.type].exists}
                } else if (schema.format) {
                    ops = {...ops, ...compOps[schema.format]}
                } else {
                    ops = {...ops, ...compOps[schema.type]}
                }
                if (schema.type === 'array' && ops.exists) {
                    ops.exists = `(${ops.exists} and {field} != [])`
                }
                if (this.valueSchema.name === 'labels') {
                    delete ops.size
                }
                return ops
            },
            opTitleTranslation() {
                return {
                    count_equals: 'count =',
                    count_below: 'count <',
                    count_above: 'count >',
                    notInSubnet: 'not in subnet',
                    subnet: 'in subnet',
                }
            },
            opsList() {
                return Object.keys(this.opsMap).map((op) => {
                    return {
                      name: op,
                      title: this.opTitleTranslation[op] ? this.opTitleTranslation[op] : op
                    }
                })
            },
            showValue() {
                return this.checkShowValue(this.condition.compOp)
            }
        },
        data() {
            return {
                condition: {...this.value},
                processedValue: ''
            }
        },
        watch: {
            isParent() {
                this.condition.field = ''
                this.condition.compOp = ''
                this.condition.value = null
                this.$emit('error', '')
            },
            value(newValue) {
                if (newValue.field !== this.condition.field) {
                    this.condition = {...newValue}
                }
            },
            conditionField() {
                if (this.condition.field.includes('id')) {
                    this.condition.compOp = 'exists'
                }
            },
            valueSchema(newSchema, oldSchema) {
                if (!newSchema || !oldSchema || this.isParent) return
                if (!oldSchema.type && !oldSchema.format) return
                if (newSchema.type !== oldSchema.type || newSchema.format !== oldSchema.format) {
                    this.condition.value = null
                }
            }
        },
        methods: {
            checkShowValue(op) {
                return this.fieldSchema && (this.fieldSchema.format === 'predefined' ||
                    (op && this.opsList.length && this.opsMap[op] && this.opsMap[op].includes('{val}')))
            },
            checkErrors() {
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
            convertSubnetToRaw(val) {
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
            formatNotInSubnet() {
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
                rawIpsArray = rawIpsArray.sort((range1,range2) => {return range1[0]-range2[0]})  
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
            formatInSubnet() {
                let subnet = this.condition.value
                let rawIps = this.convertSubnetToRaw(subnet)

                if (rawIps.length == 0) {
                    return 'Specify <address>/<CIDR> to filter IP by subnet'
                }
                this.processedValue = rawIps
                return ''
            },
            formatCondition() {
                this.processedValue = ''
                if (this.fieldSchema.format && this.fieldSchema.format === 'ip') {
                    if (this.condition.compOp === 'subnet') {
                        return this.formatInSubnet()
                    }
                    if (this.condition.compOp === 'notInSubnet') {
                        return this.formatNotInSubnet()
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
            composeCondition() {
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
            compileCondition() {
                this.$emit('input', this.condition)
                if (!this.condition.field || this.isParent) return

                let error = this.checkErrors() || this.formatCondition()
                this.$emit('error', error)
                if (error) {
                    return
                }
                this.$emit('change', this.composeCondition())
            }
        },
        updated() {
            this.compileCondition()
        },
        created() {
            if (this.condition.field) {
                this.compileCondition()
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
