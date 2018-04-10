<template>
    <triggerable-dropdown :arrow="true" size="sm" class="x-select">
        <div slot="trigger" class="x-select-trigger">
            <slot v-if="selectedOption" :option="selectedOption">{{selectedOption.title}}</slot>
            <div v-if="!value && placeholder" class="placeholder">{{placeholder}}</div>
        </div>
        <div class="x-select-content" slot="content">
            <search-input v-if="searchable" v-model="searchValue" class="x-select-search" />
            <div class="x-select-options">
                <div v-for="option in currentOptions" @click="selectOption(option.name)" class="x-select-option" >
                    <slot :option="option">{{option.title}}</slot>
                </div>
            </div>
        </div>
    </triggerable-dropdown>
</template>

<script>
    import TriggerableDropdown from '../popover/TriggerableDropdown.vue'
    import SearchInput from '../inputs/SearchInput.vue'

	export default {
		name: 'x-select',
        components: { TriggerableDropdown, SearchInput },
        props: { options: {}, value: {}, placeholder: {}, searchable: {default: false} },
        computed: {
			currentOptions() {
				if (!this.options) return []
				return this.options.filter(option => (option.name !== this.value)
                    && option.title.toLowerCase().includes(this.searchValue.toLowerCase()))
            },
            selectedOption() {
				if (!this.value || !this.options || !this.options.length) return undefined
				return this.options.filter(option => (option.name === this.value))[0]
            }
        },
        data() {
			return {
				searchValue: ''
            }
        },
        methods: {
			selectOption(name) {
				this.$emit('input', name)
                this.searchValue = ''
                this.$children[0].close()
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
            display: flex;
            padding: 0 32px 0 4px;
            height: 30px;
            line-height: 32px;
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
                    &:hover {
                        background-color: $grey-2;
                    }
                }
            }
        }
    }
</style>