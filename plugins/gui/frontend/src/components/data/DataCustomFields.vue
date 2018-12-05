<template>
    <div class="x-data-custom-fields">
        <div class="custom-fields" ref="fields">
            <div v-for="(field, i) in fieldConfig" class="fields-item" v-if="field && field.name !== 'id'">
                <template v-if="field.predefined">
                    <x-select :options="currentFieldOptions(field.name)" v-model="field.name" placeholder="Field..."
                              :searchable="true" :read-only="!field.new" :container="$refs.fields" @input="onInputValue"
                              :class="{'border-error': empty(field.name)}" />
                    <component v-if="field.name" :is="fieldMap[field.name].type" :schema="fieldMap[field.name]" v-model="field.value"
                               @input="onInputValue" :class="{'border-error': empty(field.value)}" /><div v-else></div>
                </template>
                <template v-else>
                    <div class="item-type">
                        <x-select :options="typeOptions" v-model="field.type" placeholder="Type..." :searchable="true"
                                  :class="{'border-error': empty(field.type)}" />
                        <input type="text" v-model="field.name" @keypress="validateFieldName" @input="onInputValue"
                               :class="{'border-error': empty(field.name) || duplicateFieldName(field.name)}">
                    </div>
                    <component v-if="field.type" :is="field.type" :schema="{ type: field.type }" v-model="field.value"
                               @input="onInputValue" :class="{'border-error': empty(field.value)}" /><div v-else></div>
                </template>
                <div v-if="field.new" @click="removeField(i)" class="x-btn link">X</div><div v-else></div>
            </div>
        </div>
        <div class="footer">
            <button @click="addPredefinedField" class="x-btn link">+ Predefined field</button>
            <button @click="addCustomField" class="x-btn link">+ New field</button>
            <div v-if="error" class="error-text">{{ error }}</div>
        </div>
    </div>
</template>

<script>
    import xSelect from '../inputs/Select.vue'
    import string from '../controls/string/StringEdit.vue'
    import number from '../controls/numerical/NumberEdit.vue'
    import integer from '../controls/numerical/IntegerEdit.vue'
    import bool from '../controls/boolean/BooleanEdit.vue'

    export default {
        name: 'x-data-custom-fields',
        components: { xSelect, string, number, integer, bool },
        props: {
            value: {},
            module: { required: true },
            fields: { required: true }
        },
        data() {
            return {
                fieldConfig: [],
                error: ''
            }
        },
        computed: {
            definedFields() {
                return this.fieldConfig.map(field => field.name)
            },
            fieldOptions() {
                return this.fields
                    .filter(field => !field.name.match(/\.id$/) && this.validType(field))
                    .sort((first, second) => {
                        if (first.dynamic) return -1
                        if (second.dynamic) return 1
                        return first.name > second.name
                    })
                    .map(field => {
                        return {
                            name: this.trimName(field.name), title: field.title
                        }
                    })
            },
            fieldMap() {
                return this.fields.reduce((map, field) => {
                    map[this.trimName(field.name)] = field
                    return map
                }, {})
            },
            typeOptions() {
                return [
                    {
                        name: 'string', title: 'String'
                    }, {
                        name: 'number', title: 'Float'
                    }, {
                        name: 'integer', title: 'Integer'
                    }, {
                        name: 'bool', title: 'Bool'
                    }
                ]
            }
        },
        methods: {
            currentFieldOptions(fieldName) {
                return this.fieldOptions.filter(field =>
                    !this.definedFields.includes(field.name) || field.name === fieldName)
            },
            trimName(name) {
                return name.replace(/(adapters_data|specific_data)\.(gui|data)\./g, '')
            },
            validType(field) {
                return ['string', 'bool', 'number', 'integer'].includes(field.type) &&
                    (!field.format || !field.format.match(/(date|time)/))
            },
            addPredefinedField() {
                this.fieldConfig.push({
                    predefined: true, new: true
                })
                this.$emit('validate', false)
            },
            addCustomField() {
                this.fieldConfig.push({
                    predefined: false, new: true
                })
                this.$emit('validate', false)
            },
            onInputValue() {
                let valid = true
                this.$emit('input', this.fieldConfig.reduce((map, field) => {
                    if (this.empty(field.name) || this.empty(field.value)
                        || (!field.predefined && this.duplicateFieldName(field.name))) valid = false

                    if (field.value !== undefined && field.value !== null) {
                        map[field.name] = field.value
                    }
                    return map
                }, {}))
                this.$emit('validate', valid)
            },
            removeField(index) {
                this.fieldConfig.splice(index, 1)
                this.onInputValue()
            },
            empty(value) {
                let isEmpty = (value === undefined || value === null || value === '')
                if (isEmpty) {
                    this.$emit('validate', false)
                }
                return isEmpty
            },
            validateFieldName(event) {
                event = (event) ? event : window.event;
                let charCode = (event.which) ? event.which : event.keyCode;
                if ((charCode >= 48 && charCode <= 57) || (charCode >= 65 && charCode <= 90)
                    || (charCode >= 97 && charCode <= 122) || charCode === 32 || charCode === 95) {
                    return true
                }
                event.preventDefault()
            },
            duplicateFieldName(fieldName) {
                if (this.definedFields.filter(field => {
                    if (this.fieldMap[field]) {
                        return this.fieldMap[field].title === fieldName
                    }
                    return field === fieldName
                }).length > 1 || Object.keys(this.fieldMap).includes(fieldName)) {
                    this.$emit('validate', false)
                    this.error = 'Custom Field Name is already in use by another field'
                    return true
                }
                this.error = ''
                return false
            }
        },
        created() {
            this.fieldConfig = Object.keys(this.value).map(fieldName => {
                return {
                    name: fieldName, value: this.value[fieldName], predefined: true
                }
            })
        }
    }
</script>

<style lang="scss">
    .x-data-custom-fields {
        .custom-fields {
            height: 60vh;
            overflow-y: auto;
            .fields-item {
                display: grid;
                grid-template-columns: 1fr 1fr 20px;
                grid-gap: 12px;
                margin-bottom: 12px;
                line-height: 30px;
                .item-type {
                    display: flex;
                    input {
                        flex: 1 0 auto;
                    }
                }
                .x-btn.link {
                    line-height: 30px;
                    padding: 0;
                }
                .border-error {
                    border: 1px solid $indicator-error;
                }
            }
        }
        .footer {
            display: flex;
            .error-text {
                margin-left: 24px;
                flex: 1 0 auto;
                line-height: 28px;
                text-align: right;
            }
        }
    }
</style>