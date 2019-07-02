<template>
  <x-dropdown
    ref="dropdown"
    :arrow="true"
    class="x-select"
    :size="size"
    :read-only="readOnly"
    :container="container"
  >
    <div
      :id="id"
      slot="trigger"
      class="x-select-trigger"
      :tabindex="-1"
      @keyup.down="incActiveOption"
    >
      <slot
        v-if="selectedOption"
        :option="selectedOption"
      >
        <div
          class="trigger-text"
          :title="selectedOption.title"
        >{{ selectedOption.title }}</div>
      </slot>
      <div
        v-if="!value && placeholder"
        class="placeholder"
      >{{ placeholder }}</div>
    </div>
    <div
      slot="content"
      class="x-select-content"
      @keydown.down="incActiveOption"
      @keydown.up="decActiveOption"
      @keyup.enter="selectActive"
      @keyup.esc="closeDropdown"
    >
      <x-search-input
        v-if="searchable"
        ref="searchInput"
        v-model="searchValue"
        class="x-select-search"
      />
      <div class="x-select-options">
        <div
          v-for="(option, index) in filteredOptions"
          :key="index"
          ref="option"
          class="x-select-option"
          :class="{active: index === activeOptionIndex}"
          :tabindex="-1"
          @click="selectOption(option.name)"
          @keyup.enter.stop.prevent="selectOption(option.name)"
        >
          <slot :option="option">{{ option.title }}</slot>
        </div>
      </div>
    </div>
  </x-dropdown>
</template>

<script>
  import xDropdown from '../popover/Dropdown.vue'
  import xSearchInput from '../../neurons/inputs/SearchInput.vue'

  export default {
    name: 'XSelect',
    components: { xDropdown, xSearchInput },
    props: {
      options: {
        type: Array,
        default: () => []
      },
      value: {
        type: [String],
        default: ''
      },
      placeholder: {
        type: String,
        default: ''
      },
      searchable: {
        type: Boolean,
        default: false
      },
      id: {
        type: String,
        default: undefined
      },
      size: {
        type: String,
        default: ''
      },
      alignAgile: {
        type: Boolean,
        default: true
      },
      container: {
        type: Element,
        default: undefined
      },
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        searchValue: '',
        activeOptionIndex: -1
      }
    },
    computed: {
      completeOptions () {
        if (this.value && !this.options.find(item => item.name === this.value)) {
          return [...this.options, {
            name: this.value, title: `${this.value} (deleted)`
          }]
        }
        return this.options
      },
      filteredOptions () {
        if (!this.completeOptions || !Array.isArray(this.completeOptions)) return []
        return this.completeOptions.filter(option =>
          option.title && option.title.toLowerCase().includes(this.searchValue.toLowerCase()))
      },
      selectedOption () {
        if (!this.value || !this.completeOptions || !this.completeOptions.length) return undefined
        return this.completeOptions.find(option => (option && option.name === this.value))
      }
    },
    watch: {
      filteredOptions () {
        this.activeOptionIndex = -1
      }
    },
    methods: {
      selectOption (name) {
        this.$emit('input', name)
        this.searchValue = ''
        this.closeDropdown()
      },
      closeDropdown () {
        this.$refs.dropdown.close()
      },
      incActiveOption () {
        this.focusOptions()
        this.activeOptionIndex++
        if (this.activeOptionIndex === this.filteredOptions.length) {
          this.activeOptionIndex = -1
        }
        this.scrollOption()
      },
      decActiveOption () {
        this.activeOptionIndex--
        if (this.activeOptionIndex < -1) {
          this.activeOptionIndex = this.filteredOptions.length - 1
        }
        this.scrollOption()
      },
      focusOptions () {
        if (this.searchable) {
          this.$refs.searchInput.focus()
        } else {
          this.$refs.option[0].focus()
        }
      },
      scrollOption () {
        if (this.activeOptionIndex >= 0 && this.activeOptionIndex < this.filteredOptions.length) {
          this.$refs.option[this.activeOptionIndex].scrollIntoView(false)
        }
      },
      selectActive () {
        if (this.activeOptionIndex === -1) return
        this.selectOption(this.filteredOptions[this.activeOptionIndex].name)
      }
    }
  }
</script>

<style lang="scss">
    .x-select {
        border-radius: 2px;
        border: 1px solid $grey-2;
        background: $grey-dient;

        .x-select-trigger {
            padding: 0 24px 0 4px;
            height: 30px;
            line-height: 30px;

            .trigger-text {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .placeholder {
                text-transform: uppercase;
                color: $grey-2;
            }
        }

        .x-select-content {
            font-size: 14px;
            margin: -12px -12px;

            .x-select-search {
                background-color: transparent;
            }

            .x-select-options {
                max-height: 30vh;
                overflow: auto;

                .x-select-option {
                    cursor: pointer;
                    margin: 4px 0;
                    padding: 4px 12px;

                    &:hover, &.active {
                        background-color: $grey-2;
                    }
                }
            }
        }
    }
</style>