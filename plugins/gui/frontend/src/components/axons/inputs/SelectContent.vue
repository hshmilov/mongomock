<template>
  <div
    slot="content"
    :class="{'x-select-content': true, 'x-secondary-select-content': multiSelect}"
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
      <template v-for="(currentOption, index) in filteredOptions">
        <div
          :key="index"
          ref="option"
          class="x-select-option"
          :class="{active: index === activeOptionIndex, 'filter-adapters': currentOption.plugins}"
          :tabindex="-1"
          @click="() => selectOption(currentOption.name)"
          @keyup.enter.stop.prevent="selectOption(currentOption.name)"
        >
          <x-checkbox
            v-if="multiSelect"
            :data="selectedValues[currentOption.name]"
            @change="(value) => selectOption(currentOption.name, value)"
          />
          <slot :option="getOption(currentOption)">{{ currentOption.title }}</slot>
        </div>
        <x-select-content
          v-if="currentOption.plugins !== undefined"
          slot="content"
          :key="currentOption.name"
          v-model="secondaryValues"
          :multi-select="currentOption.plugins !== undefined"
          :options="currentOption.plugins"
          :searchable="currentOption.plugins !== undefined"
        >
          <slot slot-scope="{ option }" :option="option" />
        </x-select-content>
      </template>
    </div>
    <div v-if="multiSelect" class="all-buttons">
      <div class="select-all">
        <x-button
          link
          @click="selectAllData"
        >Select all</x-button>
      </div>
      <x-button
        link
        @click="clearAllData"
      >Clear all</x-button>
    </div>
  </div>
</template>

<script>
    import xSearchInput from '../../neurons/inputs/SearchInput.vue'
    import XCheckbox from "../../axons/inputs/Checkbox.vue";
    import XButton from "../../axons/inputs/Button.vue";

    export default {
        name: 'XSelectContent',
        components: {XCheckbox, XButton, xSearchInput},
        props: {
            multiSelect: {
                type: Boolean,
                default: false
            },
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
        data() {
            return {
                activeOptionIndex: -1,
                selectAll: false,
                searchValue: ''
            }
        },
        computed: {
            completeOptions() {
                if (this.value && !this.options.find(item => item.name === this.value)) {
                    let currentOptions = [...this.options];
                    if (this.value.length > 0) {
                        currentOptions.push({
                            name: this.value, title: `${this.value} (deleted)`
                        })
                    }
                    return currentOptions;
                }
                return this.options
            },
            filteredOptions() {
                if (!this.completeOptions || !Array.isArray(this.completeOptions)) return []
                return this.completeOptions.filter(option =>
                    option.title && option.title.toLowerCase().includes(this.searchValue.toLowerCase()))
            },
            secondaryValues: {
                get() {
                    if(this.value) {
                        return this.value['secondaryValues']
                    }
                    return {}
                },
                set(secondaryValues) {
                    this.value['secondaryValues'] = secondaryValues
                    this.onOptionChanged(this.value)
                }
            },
            selectedValues: {
                get() {
                    if(this.value && !this.value['secondaryValues']){
                        return this.value['selectedValues']
                    }
                    let newSelectedValues = {}
                    this.filteredOptions.forEach(option => newSelectedValues[option.name] = true)
                    return newSelectedValues
                },
                set(selectedValues) {
                    this.onOptionChanged(selectedValues)
                }
            }
        },
        watch: {
            filteredOptions() {
                this.activeOptionIndex = -1
            }
        },
        methods: {
            selectOption(name, value) {
                if (!this.multiSelect) {
                    let currentValue = {'value': name}
                    let currentOption = this.filteredOptions.find(option => option.name === name)
                    if (currentOption.plugins && this.secondaryValues) {
                        currentValue['secondaryValues'] = this.secondaryValues;
                    } else {
                        currentValue = name
                    }
                    this.$emit('input', currentValue)
                    this.$emit('close')
                    this.searchValue = ''
                } else {
                    let newValue = value
                    if(newValue === undefined) {
                        newValue = !this.selectedValues[name]
                    }
                    if(!newValue){
                        this.selectAll = false
                    }
                    this.selectedValues = {...this.selectedValues, [name]: newValue}

                }
            },
            onOptionChanged(selectedValues){
                if(this.multiSelect){
                    this.selectAll = Object.keys(selectedValues).filter(key => selectedValues[key]).length === this.options.length
                    this.$emit('input', { selectedValues: selectedValues, selectAll: this.selectAll })
                } else {
                    this.$emit('input', selectedValues)
                }

            },
            closeDropdown() {
                this.$refs.dropdown.close()
            },
            incActiveOption() {
                this.focusOptions()
                this.activeOptionIndex++
                if (this.activeOptionIndex === this.filteredOptions.length) {
                    this.activeOptionIndex = -1
                }
                this.scrollOption()
            },
            decActiveOption() {
                this.activeOptionIndex--
                if (this.activeOptionIndex < -1) {
                    this.activeOptionIndex = this.filteredOptions.length - 1
                }
                this.scrollOption()
            },
            focusOptions() {
                if (this.searchable) {
                    this.$refs.searchInput.focus()
                } else {
                    this.$refs.option[0].focus()
                }
            },
            scrollOption() {
                if (this.activeOptionIndex >= 0 && this.activeOptionIndex < this.filteredOptions.length) {
                    this.$refs.option[this.activeOptionIndex].scrollIntoView(false)
                }
            },
            selectActive() {
                if (this.activeOptionIndex === -1) return
                this.selectOption(this.filteredOptions[this.activeOptionIndex].name)
            },
            selectAllData () {
                let selectedValues = {}
                this.selectAll = true
                this.filteredOptions.forEach(option => {
                    selectedValues[option.name] = true
                })
                this.onOptionChanged(selectedValues)
            },
            clearAllData () {
                let selectedValues = {}
                this.selectAll = false
                this.filteredOptions.forEach(option => {
                    selectedValues[option.name] = false
                })
                this.onOptionChanged(selectedValues)
            },
            getOption(currentOption){
                if(currentOption.plugins && this.value['secondaryValues']){
                    let numOfPlugins = Object.values(this.value['secondaryValues']).filter(value => value).length
                    if(numOfPlugins > 0 && numOfPlugins < currentOption.plugins.length) {
                        return {...currentOption, filtered: true}
                    }
                }
                return currentOption
            }
        }
    }
</script>

<style lang="scss">
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
        position: relative;

        &:hover, &.active {
          background-color: $grey-2;
        }

        &.filter-adapters:after {
          /*top: 53px !important;*/
          right: 15px;
          @include triangle('right', 0.35rem);
        }

      }
    }

    &.x-secondary-select-content {
      display: none;
      background-color: #FFFFFF;
      top: 50px;
      left: 220px;
      width: 260px;
      border-radius: 4px;
      box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.4), 0 2px 42px 0 rgba(0, 0, 0, 0.2);
      position: absolute;
      z-index: 100;

      .x-checkbox {
        display: inline-block;
      }

    }

    .all-buttons {
      display: flex;

      .select-all {
        flex: 1;
        text-align: left;
      }
    }
  }

  .filter-adapters:hover + .x-secondary-select-content {
    display: block;
  }

  .x-secondary-select-content:hover {
    display: block;
  }

</style>