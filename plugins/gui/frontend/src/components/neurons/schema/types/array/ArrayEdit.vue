<template>
  <div class="x-array-edit">
    <template v-if="!isItemsString">
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
        >
          <component
            :is="item.type"
            ref="itemChild"
            v-model="data[item.name]"
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
    <template v-else-if="isItemsStringEnum">
      <label>{{ schema.title }}</label>
      <md-field>
        <md-select
          v-model="data"
          placeholder="Select..."
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
      <md-chips
        v-model="data"
        ref="chips"
        md-placeholder="Add..."
        @keydown.native="checkChip"
        @focusout.native="insertChip"
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

  import arrayMixin from './array'

  export default {
    name: 'Array',
    components: {
      xTypeWrap, string, number, integer, bool, file, range, xButton
    },
    mixins: [arrayMixin],
    props: {
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        needsValidation: false
      }
    },
    computed: {
      isItemsString () {
        if (this.isOrderedObject) return false
        return this.schema.items.type === 'string'
      },
      isItemsStringEnum () {
        return this.isItemsString && this.schema.items.enum
      }
    },
    watch: {
      isHidden () {
        /*
            Change of hidden, means some fields may appear or disappear.
            Therefore, the new children should be re-validated but the DOM has not updated yet
         */
        this.needsValidation = true
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
      onValidate (validity) {
        this.$emit('validate', validity)
      },
      validate (silent) {
        if (!this.$refs.itemChild) return
        this.$refs.itemChild.forEach(item => item.validate(silent))
      },
      addNewItem () {
        this.data = [...this.data,
          this.schema.items.items.reduce((map, field) => {
            map[field.name] = field.default || null
            return map
          }, {})
        ]
      },
      removeItem (index) {
        this.data.splice(index, 1)
      },
      checkChip (event) {
        event = (event) ? event : window.event
        if (event.key !== 'Tab' && event.key !== ',' && event.key !== ';') {
          return true
        }
        this.insertChip(event)
        event.preventDefault()
      },
      insertChip(event) {
        let value = event.target.value
        if (!value) return
        let processedValue = value.split(/[;,]+/).map(item => {
          if (this.schema.items.format === 'email') {
            let emailMatch = item.match(new RegExp('.*?\s?<(\.*?)>'))
            if (emailMatch && emailMatch.length > 1) {
              return emailMatch[1]
            }
          }
          return item
        })
        this.data = Array.from(new Set(this.data.concat(processedValue)))
        this.$refs.chips.inputValue = ''
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
            .x-button.link {
                text-align: right;
            }
        }
    }
</style>