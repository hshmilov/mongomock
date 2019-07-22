<template>
  <div class="x-select-typed-field">
    <x-select-symbol
      v-if="isTyped"
      v-model="fieldType"
      :options="options"
      :minimal="minimal"
      @input="updateAutoField"
    />
    <x-select
      :id="id"
      :options="currentFields"
      :value="value"
      placeholder="field..."
      :searchable="true"
      class="field-select"
      :class="{linked: isTyped}"
      @input="$emit('input', $event)"
    />
  </div>
</template>

<script>
  import xSelectSymbol from './SelectSymbol.vue'
  import xSelect from '../../axons/inputs/Select.vue'

  export default {
    name: 'XSelectTypedField',
    components: { xSelectSymbol, xSelect },
    props: {
      options: {
        type: Array,
        required: true
      },
      value: {
        type: String,
        default: ''
      },
      id: {
        type: String,
        default: undefined
      },
      minimal: {
        type: Boolean,
        default: true
      }
    },
    data () {
      return {
        fieldType: ''
      }
    },
    computed: {
      isTyped () {
        return Boolean(this.options && this.options.length && this.options[0].fields)
      },
      currentFields () {
        if (!this.isTyped) return this.options
        if (!this.fieldType) return this.options[0].fields
        return this.options.find(item => item.name === this.fieldType).fields
      },
      firstType () {
        if (!this.options || !this.options.length) return 'axonius'
        return this.options[0].name
      }
    },
    watch: {
      value (newValue, oldValue) {
        if (newValue && newValue !== oldValue) {
          this.updateFieldType()
        } else if (!newValue) {
          this.fieldType = 'axonius'
        }
      },
      currentFields (newCurrenFields) {
        if (!this.value) return
        if (!newCurrenFields.filter(field => field.name === this.value).length) {
          this.$emit('input', '')
        }
      },
      firstType (newFirstType) {
        this.fieldType = newFirstType
      }
    },
    created () {
      this.fieldType = this.firstType
      if (this.value) {
        this.updateFieldType()
        this.$emit('input', this.value)
      }
    },
    methods: {
      updateFieldType () {
        let fieldSpaceMatch = /adapters_data\.(\w+)\./.exec(this.value)
        if (fieldSpaceMatch && fieldSpaceMatch.length > 1) {
          this.fieldType = fieldSpaceMatch[1]
        } else {
          this.fieldType = 'axonius'
        }
      },
      updateAutoField () {
        if (!this.isTyped || this.fieldType === '' || this.fieldType === 'axonius') {
          return
        }
        if (this.value) {
          let fieldMatch = /\w+_data\.\w+\.(\w+)/.exec(this.value)
          if (fieldMatch && fieldMatch.length > 1) {
            let currentField = this.currentFields.find(field => field.name.includes(fieldMatch[1]))
            if (currentField) {
              this.$emit('input', currentField.name)
              return
            }
          }
        }
        if (this.currentFields.find(field => field.name.includes('.id'))) {
          this.$emit('input', `adapters_data.${this.fieldType}.id`)
        }
      }
    }
  }
</script>

<style lang="scss">
    .x-select-typed-field {
        display: flex;
        width: 100%;

        .x-select-symbol {
            border-bottom-right-radius: 0;
            border-top-right-radius: 0;
            .logo-text {
                max-width: 178px;
            }
        }

        .field-select {
            flex: 1 0 auto;
            width: 120px;
            margin-left: 60px;

            &.linked {
                width: 180px;
                margin-left: -2px;
                border-bottom-left-radius: 0;
                border-top-left-radius: 0;
            }
        }
    }
</style>