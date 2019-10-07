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
      class="view-name"
    />
    <div />
    <div />
    <x-select-typed-field
      v-model="fieldName"
      :options="fieldOptions"
    />
    <div />
  </div>
</template>

<script>
  import xSelect from '../../../axons/inputs/Select.vue'
  import xSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue'
  import xSelectTypedField from '../../../neurons/inputs/SelectTypedField.vue'
  import chartMixin from './chart'
  import {isObjectListField} from '../../../../constants/utils'

  import { mapGetters } from 'vuex'
  import { GET_DATA_FIELDS_BY_PLUGIN, GET_DATA_SCHEMA_BY_NAME } from '../../../../store/getters'

  export default {
    name: 'XChartSegment',
    components: { xSelect, xSelectSymbol, xSelectTypedField },
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
      },
      updateView(view) {
      },
    }
  }
</script>

<style lang="scss">

</style>
