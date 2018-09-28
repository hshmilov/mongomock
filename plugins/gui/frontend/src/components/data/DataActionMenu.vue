<template>
    <div>
        <triggerable-dropdown size="sm" align="right" :arrow="false">
            <div slot="trigger" class="x-btn link">Actions</div>
            <nested-menu slot="content">
                <nested-menu-item v-for="item in $children" v-if="item.title" :key="item.title"
                                  :title="item.title" @click="activate(item)"/>
            </nested-menu>
        </triggerable-dropdown>
        <x-tag-modal title="Tag..." :module="module" :entities="selected" :tags="currentTags" />
        <x-data-action-item title="Disable..." :handle-save="disableEntities" :message="`Disabled ${module}`"
                            action-text="Disable">
            <div>Out of {{selected.length}} {{module}}, {{disableable.length}} could be disabled.</div>
            <div>These {{module}} will not appear in further scans.</div>
            <div>Are you sure you want to continue?</div>
        </x-data-action-item>
        <x-data-action-item title="Delete..." :handle-save="deleteEntities" :message="`Deleted ${module}`"
                            action-text="Delete">
            <div>You are about to delete {{selected.length}} {{module}}, {{selectedAdaptersCount}} total adapter {{module}}.</div>
            <div>These {{module}} could reappear in further scans if they're not removed or detached.</div>
            <div>Are you sure you want to delete these {{module}}?</div>
        </x-data-action-item>
        <slot></slot>
    </div>
</template>

<script>
	import TriggerableDropdown from '../popover/Dropdown.vue'
	import NestedMenu from '../../components/menus/NestedMenu.vue'
	import NestedMenuItem from '../../components/menus/NestedMenuItem.vue'
    import xDataActionItem from '../../components/data/DataActionItem.vue'
	import xTagModal from '../../components/popover/TagModal.vue'

	import { mapGetters, mapActions } from 'vuex'
    import { GET_DATA_BY_ID } from '../../store/getters'
    import { DELETE_DATA, DISABLE_DATA, REQUEST_API } from '../../store/actions'

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
        props: { module: {required: true}, selected: {required: true} },
        computed: {
			...mapGetters({getDataByID: GET_DATA_BY_ID }),
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
				return this.selected.filter(entityID => {
					let entity = this.dataByID[entityID]
					if (!entity) return false
					return entity.unique_adapter_names.some((uniqueName) => {
                        let adapter = this.adapterFeatures[uniqueName]
                        return adapter && adapter.includes(disableableByModule[this.module])
                    })
				})
            },
            selectedAdaptersCount() {
                let count = 0
                this.selected.forEach(entity => {
                    count += this.dataByID[entity].adapters.length
                })
                return count
            }
        },
        data() {
		     return {
                 adapterFeatures: {}
             }
        },
        methods: {
            ...mapActions({ disableData: DISABLE_DATA, deleteData: DELETE_DATA, fetchData: REQUEST_API }),
            activate(item) {
            	if (!item || !item.activate) return
                item.activate()
                this.$el.click()
            },
			disableEntities() {
				return this.disableData({ module: this.module, data: this.disableable })
			},
            deleteEntities() {
                return this.deleteData({ module: this.module, data: {
                        internal_axon_ids: this.selected
                    }}).then(() => this.$emit('done'))
            }
        },
        created() {
			this.fetchData({
                rule: 'adapter_features'
            }).then((response) => {
                this.adapterFeatures = response.data
            })
        }
	}
</script>

<style lang="scss">

</style>