<template>
    <div>
        <triggerable-dropdown size="sm" align="right" :arrow="false">
            <div slot="trigger" class="x-btn link">Actions</div>
            <nested-menu slot="content">
                <nested-menu-item v-for="item in $children" v-if="item.title" :key="item.title"
                                  :title="item.title" @click="activate(item)"/>
            </nested-menu>
        </triggerable-dropdown>
        <x-tag-modal title="Tag..." :module="module" :entities="selected" :tags="currentTags" ref="tag" />
        <x-data-action-item title="Disable..." :handle-save="disableEntities" :message="`Disabled ${module}`" ref="disable" >
            <div>Out of {{selected.length}} {{module}}, {{disableable.length}} could be disabled.</div>
            <div>These {{module}} will not appear in further scans.</div>
            <div>Are you sure you want to continue?</div>
        </x-data-action-item>
            <x-data-action-item title="Delete..." :handle-save="deleteEntities" :message="`Deleted ${module}`" ref="disable" >
            <div>You are about to delete {{selected.length}} {{module}}, {{selectedAdaptersCount}} total adapter
                {{module}}.</div>
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

	import { mapState, mapGetters, mapActions } from 'vuex'
    import { FETCH_ADAPTERS } from '../../store/modules/adapter'
	import { GET_DATA_BY_ID } from '../../store/getters'
    import { DELETE_DATA, DISABLE_DATA } from '../../store/actions'

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
            ...mapState({
                adapterByUniqueName(state) {
                	let adapterData = state.adapter.adapterList.data
					if (!adapterData || !adapterData.length) return {}
					return adapterData.reduce((map, input) => {
						map[input.unique_plugin_name] = input
						return map
					}, {})
                }
            }),
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
                        let adapter = this.adapterByUniqueName[uniqueName]
                        return adapter && adapter.supported_features.includes(disableableByModule[this.module])
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
        methods: {
            ...mapActions({ disableData: DISABLE_DATA, deleteData: DELETE_DATA, fetchAdapters: FETCH_ADAPTERS }),
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
			this.fetchAdapters()
        }
	}
</script>

<style lang="scss">

</style>