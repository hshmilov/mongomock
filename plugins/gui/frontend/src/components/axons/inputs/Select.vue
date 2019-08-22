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
    <x-select-content
      slot="content"
      v-model="selectContentValue"
      :multi-select="false"
      :options="options"
      :searchable="searchable"
      :read-only="readOnly"
      @close="() => closeDropdown()"
    ><slot
      slot-scope="{ option }"
      :option="option"
    />
    </x-select-content>
  </x-dropdown>
</template>

<script>
  import xDropdown from '../popover/Dropdown.vue'
  import xSelectContent from './SelectContent.vue'

  export default {
    name: 'XSelect',
    components: { xDropdown, xSelectContent },
    props: {
      options: {
        type: Array,
        default: () => []
      },
      value: {
        type: [String, Object],
        default: null
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
    computed: {
      completeOptions () {
        if (this.stringValue && !this.options.find(item => item.name === this.stringValue)) {
          return [...this.options, {
            name: this.stringValue, title: `${this.stringValue} (deleted)`
          }]
        }
        return this.options
      },
      selectedOption () {
        if (!this.stringValue || !this.completeOptions || !this.completeOptions.length) return undefined
        return this.completeOptions.find(option => (option && option.name === this.stringValue));
      },
      selectContentValue: {
        get() {
            return this.value
        },
        set(value) {
            this.$emit('input', value)
        }
      },
      stringValue() {
          return !this.value || typeof(this.value) === 'string' ? this.value : this.value['value']
      }
    },
    methods: {
      selectOption (value) {
        this.$emit('input', value)
        this.closeDropdown()
      },
      closeDropdown () {
        this.$refs.dropdown.close()
      }
    },
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