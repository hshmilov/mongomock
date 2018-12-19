<template>
    <x-dropdown :arrow="true" class="x-select" ref="dropdown" :size="size" :read-only="readOnly" :container="container">
        <div slot="trigger" class="x-select-trigger" @keyup.down="incActiveOption" :tabindex="-1" :id="id">
            <slot v-if="selectedOption" :option="selectedOption">
                <div class="trigger-text" :title="selectedOption.title">{{selectedOption.title}}</div>
            </slot>
            <div v-if="!value && placeholder" class="placeholder">{{placeholder}}</div>
        </div>
        <div slot="content" class="x-select-content" @keydown.down="incActiveOption" @keydown.up="decActiveOption"
             @keyup.enter="selectActive" @keyup.esc="closeDropdown">
            <search-input v-if="searchable" v-model="searchValue" class="x-select-search" ref="searchInput" />
            <div class="x-select-options">
                <div v-for="option, index in currentOptions"
                     @click="selectOption(option.name)" @keyup.enter.stop.prevent="selectOption(option.name)"
                     class="x-select-option" :class="{active: index === activeOptionIndex}" :tabindex="-1" ref="option">
                    <slot :option="option">{{option.title}}</slot>
                </div>
            </div>
        </div>
    </x-dropdown>
</template>

<script>
    import xDropdown from '../popover/Dropdown.vue'
    import SearchInput from '../inputs/SearchInput.vue'

	export default {
		name: 'x-select',
        components: { xDropdown, SearchInput },
        props: {
		    options: {}, value: {}, placeholder: {}, searchable: { default: false }, id: {}, size: {},
		    container: {}, readOnly: { default: false }
        },
        computed: {
			currentOptions() {
				if (!this.options) return []
				return this.options.filter(option =>
                    option.title && option.title.toLowerCase().includes(this.searchValue.toLowerCase()))
            },
            selectedOption() {
				if (!this.value || !this.options || !this.options.length) return undefined
				return this.options.find(option => (option && option.name === this.value))
            }
        },
        data() {
			return {
				searchValue: '',
                activeOptionIndex: -1
            }
        },
        watch: {
			currentOptions() {
				this.activeOptionIndex = -1
            }
        },
        methods: {
			selectOption(name) {
				this.$emit('input', name)
                this.searchValue = ''
                this.closeDropdown()
            },
            closeDropdown() {
				this.$refs.dropdown.close()
            },
			incActiveOption() {
				this.focusOptions()
                this.activeOptionIndex++
                if (this.activeOptionIndex === this.currentOptions.length) {
                	this.activeOptionIndex = -1
                }
                this.scrollOption()
            },
            decActiveOption() {
				this.activeOptionIndex--
                if (this.activeOptionIndex < -1) {
					this.activeOptionIndex = this.currentOptions.length - 1
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
				if (this.activeOptionIndex >= 0 && this.activeOptionIndex < this.currentOptions.length) {
					this.$refs.option[this.activeOptionIndex].scrollIntoView(false)
				}
            },
            selectActive() {
				if (this.activeOptionIndex === -1) return
                this.selectOption(this.currentOptions[this.activeOptionIndex].name)
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