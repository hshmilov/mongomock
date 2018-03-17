<template>
    <triggerable-dropdown size="sm" align="right" class="graded-multi-select" :arrow="false">
        <div slot="dropdownTrigger" class="link">{{ placeholder }}</div>
        <template slot="dropdownContent">
            <nested-menu>
                <nested-menu-item v-for="option, ind in options" v-if="option.fields" :title="option.title" :key="ind"
                                  v-on:mouseover="currentOption = option"><div/></nested-menu-item>
            </nested-menu>
            <dynamic-popover size="md" left="-360" v-if="this.currentOption.fields && this.currentOption.fields.length">
                <searchable-checklist :items="currentOption.fields" :searchable="true"
                                      v-model="selectedByTitle[currentOption.title]" @input="onInput"/>
            </dynamic-popover>
        </template>
    </triggerable-dropdown>
</template>

<script>
	import TriggerableDropdown from './popover/TriggerableDropdown.vue'
	import NestedMenu from './menus/NestedMenu.vue'
	import NestedMenuItem from './menus/NestedMenuItem.vue'
	import DynamicPopover from './popover/DynamicPopover.vue'
    import SearchableChecklist from './SearchableChecklist.vue'

	export default {
		name: 'x-graded-multi-select',
        components: {TriggerableDropdown, NestedMenu, NestedMenuItem, DynamicPopover, SearchableChecklist },
		props: ['value', 'options', 'placeholder'],
        watch: {
			value() {
				this.fillSelected()
            },
            options() {
				this.fillSelected()
            }
        },
        data() {
			return {
				currentOption: {fields:[]},
				selectedByTitle: {}
			}
        },
        methods: {
			fillSelected() {
				if (!this.options || !this.value) return

				this.options.forEach((option) => {
					if (!option.title || !option.fields) return

					this.selectedByTitle[option.title] = option.fields.map((field) => field.name)
						.filter((fieldName) => this.value.includes(fieldName))
				})
            },
			onInput() {
				this.$emit('input', Object.values(this.selectedByTitle).reduce((allSelected, titleSelected) => {
					return allSelected.concat(titleSelected)
                }, []))
            }
        },
        created() {
            this.fillSelected()
        }
	}
</script>

<style lang="scss">
    .graded-multi-select {
        .menu {
            max-height: 480px;
            overflow: auto;
        }
    }
</style>