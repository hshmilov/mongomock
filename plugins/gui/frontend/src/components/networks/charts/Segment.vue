<template>
    <div class="x-chart-metric">
        <x-select-symbol :options="entities" v-model="config.entity" type="icon" placeholder="module..."/>
        <x-select :options="views[config.entity] || []" :searchable="true" v-model="config.view"
                  placeholder="query (or empty for all)"/>
        <div></div>
        <div></div>
        <x-select-typed-field :options="fieldOptions" :value="config.field.name" @input="updateField"/>
        <div></div>
    </div>
</template>

<script>
    import xSelect from '../../axons/inputs/Select.vue'
    import xSelectSymbol from '../../neurons/inputs/SelectSymbol.vue'
    import xSelectTypedField from '../../neurons/inputs/SelectTypedField.vue'
    import ChartMixin from './chart'

    import {mapGetters} from 'vuex'
    import {GET_DATA_FIELDS_BY_PLUGIN, GET_DATA_SCHEMA_BY_NAME} from '../../../store/getters'

    export default {
        name: 'x-chart-segment',
        components: {xSelect, xSelectSymbol, xSelectTypedField},
        mixins: [ChartMixin],
        computed: {
            ...mapGetters({
                getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME
            }),
            fieldOptions() {
                if (!this.config.entity) return []
                return this.getDataFieldsByPlugin(this.config.entity).map(category => {
                    return {
                        ...category, fields: category.fields.filter(field => {
                            return !field.branched && field.type !== 'array'
                        })
                    }
                })
            },
            schemaByName() {
                if (!this.config.entity) return {}
                return this.getDataSchemaByName(this.config.entity)
            }
        },
        data() {
            return {
                config: {entity: '', view: '', field: {name: ''}}
            }
        },
        methods: {
            updateField(fieldName) {
                this.config.field = this.schemaByName[fieldName]
            },
            validate() {
                this.$emit('validate', this.config.field.name)
            }
        }
    }
</script>

<style lang="scss">

</style>