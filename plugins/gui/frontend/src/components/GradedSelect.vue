<template>
    <triggerable-dropdown size="sm" align="left" class="graded-select">
        <div slot="dropdownTrigger" class="">{{ selectedTitle? selectedTitle: placeholder }}</div>
        <nested-menu slot="dropdownContent">
            <nested-menu-item v-for="option, ind in options" v-if="!option.fields || option.fields.length"
                              :title="option.title" :key="ind" @click="onSelect(option.name)">
                <dynamic-popover v-if="option.fields" size="sm" left="236" :alignBottom="ind > 6">
                    <nested-menu class="inner">
                        <nested-menu-item v-for="field in option.fields" :key="field.name" :title="field.title"
                                          @click="onSelect(field.name)"/>
                    </nested-menu>
                </dynamic-popover>
            </nested-menu-item>
        </nested-menu>
    </triggerable-dropdown>
</template>

<script>
    import TriggerableDropdown from './popover/TriggerableDropdown.vue'
	import NestedMenu from './menus/NestedMenu.vue'
	import NestedMenuItem from './menus/NestedMenuItem.vue'
	import DynamicPopover from './popover/DynamicPopover.vue'

	export default {
		name: 'x-graded-select',
		components: { TriggerableDropdown, NestedMenu, NestedMenuItem, DynamicPopover },
		props: ['value', 'options', 'placeholder'],
		model: {
            prop: 'value',
            event: 'change'
        },
        computed: {
			selectedTitle() {
				if (!this.value) return ''
                let title = ''
                this.options.forEach((option) => {
					if (option.name && option.name === this.value) {
						title = option.title
                        return
                    }
                    if (!option.fields) return

                    option.fields.forEach((field) => {
						if (field.name && field.name === this.value) title =  field.title
                    })
                })
                return title
            }
        },
        methods: {
			onSelect(name) {
				if (!name) return
				this.$emit('change', name)
                this.$el.parentElement.click()
			}
		}

	}
</script>

<style lang="scss">
    .graded-select.dropdown {
        width: 100%;
        height: 30px;
        .dropdown-toggle {
            line-height: 28px;
            padding-left: 8px;
            border-radius: 4px;
            border: 1px solid #ccc;
        }
        .dropdown-menu {
            .menu.inner {
                max-height: 30vh;
                overflow: auto;
            }
        }
    }
</style>