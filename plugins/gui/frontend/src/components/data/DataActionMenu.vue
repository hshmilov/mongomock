<template>
    <div>
        <triggerable-dropdown size="sm" align="right" :arrow="false">
            <div slot="trigger" class="link">Actions</div>
            <nested-menu slot="content">
                <nested-menu-item v-for="item in $children" v-if="item.title" :key="item.title"
                                  :title="item.title" @click="activate(item)"/>
            </nested-menu>
        </triggerable-dropdown>
        <x-tag-modal title="Tag..." :module="module" :entities="selected" :tags="currentTags" ref="tag" />
        <x-data-action-item title="Disable..." :handle-save="disableEntities" :message="`Disable ${module}s`" ref="disable" >
            <div>Out of {{selected.length}} {{module}}s, {{disableable.length}} are disableable.</div>
            <div>These {{module}}s will not appear in further scans.</div>
            <div>Are you sure you want to continue?</div>
        </x-data-action-item>
        <slot></slot>
    </div>
</template>

<script>
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
	import NestedMenu from '../../components/menus/NestedMenu.vue'
	import NestedMenuItem from '../../components/menus/NestedMenuItem.vue'
    import xDataActionItem from '../../components/data/DataActionItem.vue'
	import xTagModal from '../../components/popover/TagModal.vue'

	import { mapGetters, mapActions } from 'vuex'
    import { GET_ADAPTER_BY_UNIQUE_NAME } from '../../store/modules/adapter'
	import { GET_DATA_BY_ID } from '../../store/getters'
    import { DISABLE_DATA } from '../../store/actions'

    const disableableByModule = {
		'devices': 'Devicedisabelable',
        'users': 'Userdisabelable'
    }
	export default {
		name: 'x-data-action-menu',
        components: {
			TriggerableDropdown, 'nested-menu': NestedMenu, 'nested-menu-item': NestedMenuItem,
            xDataActionItem, xTagModal
        },
        props: {module: {required: true}, selected: {required: true}},
        computed: {
			...mapGetters({getDataByID: GET_DATA_BY_ID, getAdapterByUniqueName: GET_ADAPTER_BY_UNIQUE_NAME }),
			dataByID() {
                return this.getDataByID(this.module)
            },
			currentTags() {
				if (!this.selected || !this.selected.length || !this.dataByID[this.selected[0]]) return []

				let labels = this.dataByID[this.selected[0]].labels
				if (this.selected.length === 1) return labels

				this.selected.forEach((entity) => {
					let entityLabels = this.dataByID[entity].labels
					if (!entityLabels || !entityLabels.length) {
						labels = []
						return
					}
					labels = labels.filter((label) => {
						return entityLabels.includes(label)
					})
				})
				return labels
            },
            disableable() {
				return this.module.charAt(0).toUpperCase() + this.module.substr(1)
            },
            disableable() {
				return this.selected.filter(entityID => {
					let entity = this.dataByID[entityID]
					if (!entity) return false
					return entity.unique_adapter_names.some((uniqueName) => {
                        let adapter = this.getAdapterByUniqueName[uniqueName]
                        return adapter && adapter.supported_features.includes(disableableByModule[this.module])
                    })
				})
            }
        },
        methods: {
            ...mapActions({disableData: DISABLE_DATA}),
            activate(item) {
            	if (!item || !item.activate) return
                item.activate()
                this.$el.click()
            },
			disableEntities() {
				return this.disableData({ module: this.module, data: this.disableable })
			}
        }
	}
</script>

<style lang="scss">

</style>