<template>
  <div class="x-array-edit">
    <template v-if="!isStringList">
      <h4
        v-if="schema.title"
        :id="schema.name"
        :title="schema.description || ''"
        class="array-header"
      >{{ schema.title }}</h4>
      <div
        v-for="(item, index) in shownSchemaItems"
        :key="item.name"
        class="item"
      >
        <x-type-wrap
          :name="item.name"
          :type="item.type"
          :title="item.title"
          :description="item.description"
          :required="item.required"
          :expand="!isFileList"
        >
          <component
            :is="item.type"
            ref="itemChild"
            :value="data[item.name]"
            @input="(value) => dataChanged(value, item.name)"
            :schema="item"
            :api-upload="apiUpload"
            :read-only="readOnly"
            @validate="onValidate"
          />
        </x-type-wrap>
        <x-button
          v-if="!isOrderedObject"
          link
          @click.prevent="removeItem(index)"
        >x</x-button>
      </div>
      <x-button
        v-if="!isOrderedObject"
        light
        @click.prevent="addNewItem"
      >+</x-button>
    </template>
    <template v-else-if="isStringList && schema.items.enum">
      <label>{{ schema.title }}</label>
      <md-field>
        <md-select
          v-model="data"
          :placeholder="placeholder"
          multiple
        >
          <md-option
            v-for="option in schema.items.enum"
            :key="option.name"
            :value="option.name"
          >{{ option.title }}</md-option>
        </md-select>
      </md-field>
    </template>
    <template v-else>
      <label>{{ schema.title }}</label>
      <x-list-input
        v-model="data"
        :id="schema.name"
        :format="formatStringItem"
        :error-items="invalidStringItems"
        :class="{'error-border': !stringListValid}"
        @focusout.native="() => validateStringList()"
        :readOnly="readOnly"
      />
    </template>
  </div>
</template>

<script>
  import xTypeWrap from './TypeWrap.vue'
  import string from '../string/StringEdit.vue'
  import number from '../numerical/NumberEdit.vue'
  import integer from '../numerical/IntegerEdit.vue'
  import bool from '../boolean/BooleanEdit.vue'
  import file from './FileEdit.vue'
  import range from '../string/RangeEdit.vue'
  import xButton from '../../../../axons/inputs/Button.vue'
  import xListInput from '../../../../axons/inputs/ListInput.vue'
  import { validateEmail } from '../../../../../constants/validations'

  import arrayMixin from './array'

  export default {
    name: 'Array',
    components: {
      xTypeWrap, string, number, integer, bool, file, range, xButton, xListInput
    },
    mixins: [arrayMixin],
    props: {
      readOnly: {
        type: Boolean,
        default: false
      },
      placeholder: {
        type: String,
        default: 'Select...'
      }
    },
    data () {
      return {
        needsValidation: false,
        stringListValid: true
      }
    },
    computed: {
      isStringList () {
        if (this.isOrderedObject) return false
        return this.schema.items.type === 'string'
      },
      isFileList () {
        if (this.isOrderedObject) return false
        return this.schema.items.type === 'file'
      },
      invalidStringItems() {
        if (!this.isStringList) return []
        return this.data.filter(item => {
          if (this.schema.items.format === 'email') {
            return !validateEmail(item)
          }
          return false
        })
      },
      stringListError() {
        if (this.invalidStringItems.length) {
          return `'${this.schema.title}' items are not all properly formed`
        } else if (this.data.length === 0 && this.schema.required) {
          return `'${this.schema.title}' is required`
        }
        return ''
      }
    },
    watch: {
      isHidden () {
        /*
            Change of hidden, means some fields may appear or disappear.
            Therefore, the new children should be re-validated but the DOM has not updated yet
         */
        this.needsValidation = true
      },
      stringListError () {
        this.validateStringList()
      }
    },
    mounted () {
      this.validate(true)
    },
    updated () {
      if (this.needsValidation) {
        // Here the new children (after change of hidden) are updated in the DOM
        this.validate(true)
        this.needsValidation = false
      }
    },
    methods: {
      dataChanged(value, itemName) {
        if (Array.isArray(this.data) && typeof itemName === 'number') {
          this.data = this.data.map((item, index) => index === itemName? value : item)
        } else {
          this.data = {...this.data, [itemName]: value}
        }
      },
      onValidate (validity) {
        this.$emit('validate', validity)
      },
      validate (silent) {
        if (this.isStringList) {
          this.validateStringList(silent)
        } else if (this.$refs.itemChild) {
          this.$refs.itemChild.forEach(item => item.validate(silent))
        }
      },
      addNewItem () {
        if (!this.schema.items.items) {
          this.data = [...this.data, null]
        } else {
          this.data = [...this.data,
            this.schema.items.items.reduce((map, field) => {
              map[field.name] = field.default || null
              return map
            }, {})
          ]
        }
      },
      removeItem (index) {
        this.data.splice(index, 1)
      },
      formatStringItem(item) {
        if (this.schema.items.format === 'email') {
          let emailMatch = item.match(new RegExp('.*?\s?<(\.*?)>'))
          if (emailMatch && emailMatch.length > 1) {
            return emailMatch[1]
          }
        }
        return item
      },
      validateStringList(silent) {
        let valid = this.stringListError === ''
        this.stringListValid = valid || silent
        this.$emit('validate', {
          name: this.schema.name,
          valid,
          error: this.stringListValid? '': this.stringListError
        })
      }
    }
  }
</script>

<style lang="scss">
  .x-array-edit {
    .array-header {
      margin-bottom: 0;
      display: inline-block;
      min-width: 200px;
    }

    .item {
      display: flex;
      align-items: flex-end;

      .index {
        display: inline-block;
        vertical-align: top;
      }

      .x-button {
        &.link {
          text-align: right;
        }
        &.light {
          margin-top: 8px;
          display: block;
        }
      }
    }

    .object {

      input, select, textarea {
        width: 100%;
      }

      .upload-file {
        margin-top: 8px;
      }
    }
  }
</style>