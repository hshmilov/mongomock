<template>
  <md-chips
    ref="chips"
    v-model="data"
    md-placeholder="Add..."
    :md-format="undoInsert"
    :md-static="readOnly"
    :class="{selected: allSelected}"
    @md-click="editChip"
    @keydown.native="processInsertChip"
    @keydown.control.native="keys.control = true"
    @keyup.control.native="keys.control = false"
    @keydown.a.native="selectAll"
    @keyup.a.native="keys.a = false"
    @keydown.backspace.native="removeAll"
    @focusout.native="onFocusout"
  >
    <template
      slot="md-chip"
      slot-scope="{ chip }"
    >
      <div
        class="text"
        :class="{'bg-error': errorItems.includes(chip)}"
      >{{ chip }}</div>
    </template>
  </md-chips>
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
        type: Function,
        default: () => () => {}
      },
      errorItems: {
        type: Array,
        default: () => []
      },
      readOnly: {
        default: false
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
        if(this.readOnly){
          return
        }
        this.chips.inputValue = text
        this.data.splice(index, 1)
        this.editedIndex = index
        this.placeInputForEdit()
        this.chips.$refs.input.$el.focus()
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
        if ((event.key !== 'Tab' || !this.$refs.chips.inputValue) && event.key !== ',' && event.key !== ';' && event.key !== 'Enter') {
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
        this.insertChip(event)
      },
      insertChip(event) {
        let value = event.target.value
        if (!value) {
          if (this.editedIndex !== -1 && !this.$refs.chips.inputValue) {
            this.placeInputForInsert()
          }
          return
        }
        let processedValue = value.split(/[;,]+/).map(this.format)
        if (this.editedIndex !== -1) {
          processedValue = [ ...processedValue, ...this.data.splice(this.editedIndex)]
          this.placeInputForInsert()
        }
        this.data = Array.from(new Set(this.data.concat(processedValue)))
        this.$refs.chips.inputValue = ''
      },
      placeInputForEdit() {
        let chipsEl = this.chips.$children[0].$el
        let chipsElChildren = chipsEl.children
        chipsEl.insertBefore(chipsElChildren[chipsElChildren.length - 1], chipsElChildren[this.editedIndex])
        this.chips.$refs.input.$el.classList.add('inline')
      },
      placeInputForInsert() {
        let chipsEl = this.chips.$children[0].$el
        let chipsElChildren = chipsEl.children
        chipsEl.insertBefore(chipsElChildren[this.editedIndex], chipsElChildren[chipsElChildren.length - 1].nextElementSibling)
        this.chips.$refs.input.$el.classList.remove('inline')
        this.editedIndex = -1
        this.chips.$refs.input.$el.focus()
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
        flex: 0;
        margin: 0 8px;
      }
    }
    .md-chip {
      background-color: $grey-1;
      height: 24px;
      line-height: 24px;
      .md-ripple {
        padding: 0;
        .text {
          padding: 0 32px 0 12px;
          &.bg-error {
            background-color: $indicator-error;
            border-radius: 32px;
          }
        }
      }
    }
    &.selected {
      .md-chip {
        background-color: $grey-3;
      }
    }
    &.error-border:after {
      background-color: $indicator-error;
    }
  }
</style>