<template>
  <md-chips
    ref="chips"
    v-model="data"
    md-placeholder="Add..."
    :md-format="undoInsert"
    :class="{selected: allSelected}"
    @md-click="editChip"
    @keydown.native="processInsertChip"
    @keydown.control.native="keys.control = true"
    @keyup.control.native="keys.control = false"
    @keydown.a.native="selectAll"
    @keyup.a.native="keys.a = false"
    @keydown.backspace.native="removeAll"
    @focusout.native="onFocusout"
  />
</template>

<script>
  export default {
    name: 'XListInput',
    props: {
      value: {
        type: Array,
        default: () => []
      },
      format: {
        type: String,
        default: ''
      }
    },
    data() {
      return {
        keys: {
          control: false,
          a: false
        },
        allSelected: false,
        insertedChip: '',
        editedIndex: -1
      }
    },
    computed: {
      data: {
        get() {
          return this.value
        },
        set(value) {
          this.$emit('input', value)
        }
      },
      chips() {
        return this.$refs.chips
      }
    },
    methods: {
      undoInsert(value) {
        this.insertedChip = value
        return ''
      },
      editChip(text, index) {
        this.chips.inputValue = text
        this.data.splice(index, 1)
        this.editedIndex = index
        this.inputToEditIndex()
        this.chips.$refs.input.$el.focus()
        this.chips.$refs.input.$el.classList.add('inline')
      },
      selectAll() {
        this.keys.a = true
        if (this.keys.control && this.data.length) this.allSelected = true
      },
      removeAll() {
        if (this.allSelected) {
          this.data = []
          this.allSelected = false
        }
      },
      processInsertChip (event) {
        event = (event) ? event : window.event
        if (event.key !== 'Tab' && event.key !== ',' && event.key !== ';' && event.key !== 'Enter') {
          return true
        }
        if (event.key === 'Enter') {
          event.target.value = this.insertedChip
          this.insertedChip = ''
        }
        this.insertChip(event)
        event.preventDefault()
      },
      onFocusout(event) {
        this.allSelected = false
        this.editedIndex = -1
        this.insertChip(event)
      },
      insertChip(event) {
        let value = event.target.value
        if (!value) return
        let processedValue = value.split(/[;,]+/).map(item => {
          if (this.format === 'email') {
            let emailMatch = item.match(new RegExp('.*?\s?<(\.*?)>'))
            if (emailMatch && emailMatch.length > 1) {
              return emailMatch[1]
            }
          }
          return item
        })
        if (this.editedIndex !== -1) {
          this.inputToEditIndex()
          processedValue = processedValue.concat(this.data.splice(this.editedIndex))
          this.chips.$refs.input.$el.classList.remove('inline')
          this.editedIndex = -1
        }
        this.data = Array.from(new Set(this.data.concat(processedValue)))
        this.$refs.chips.inputValue = ''
      },
      inputToEditIndex() {
        let chipsEl = this.chips.$children[0].$el
        let chipsElChildren = chipsEl.children
        chipsEl.insertBefore(chipsElChildren[chipsElChildren.length - 1], chipsElChildren[this.editedIndex])
      }
    }
  }
</script>

<style lang="scss">
  .md-field.md-chips {
    margin-bottom: 0;
    padding-top: 0;
    min-height: auto;
    &:after {
      background-color: $grey-2;
    }
    .md-input {
      border: 0;
      font-size: 14px;
      height: 28px;
      &.inline {
        flex: 0
      }
    }
    .md-chip {
      background-color: $grey-1;
      height: 24px;
      line-height: 24px;
    }
    &.selected {
      .md-chip {
        background-color: $grey-3;
      }
    }
  }
</style>