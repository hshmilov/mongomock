<template>
    <div>
        <x-dropdown size="sm" align="right" :arrow="false" ref="dropdown">
            <button slot="trigger" class="x-btn link">Actions</button>
            <nested-menu slot="content">
                <nested-menu-item v-for="item in $children" v-if="item.title" :key="item.title"
                                  :title="item.title" @click="activate(item)"/>
            </nested-menu>
        </x-dropdown>
        <x-tag-modal title="Tag..." :module="module" :entities="entities" :value="currentTags" />
        <x-data-action-item title="Disable..." :handle-save="disableEntities" :message="`Disabled ${module}`"
                            action-text="Disable">
            <div>You are about to disable {{ selectionCount }} {{ module }}.</div>
            <div>These {{module}} will not appear in further scans.</div>
            <div>Are you sure you want to continue?</div>
        </x-data-action-item>
        <x-data-action-item title="Delete..." :handle-save="deleteEntities" :message="`Deleted ${module}`"
                            action-text="Delete">
            <div class="warn-delete">You are about to delete {{ selectionCount }} {{module}}.</div>
            <div>These {{module}} could reappear in further scans if they are not removed or detached.</div>
            <div>Are you sure you want to delete these {{module}}?</div>
        </x-data-action-item>
        <slot></slot>
    </div>
</template>

<script>
	import xDropdown from '../popover/Dropdown.vue'
	import NestedMenu from '../../components/menus/NestedMenu.vue'
	import NestedMenuItem from '../../components/menus/NestedMenuItem.vue'
    import xDataActionItem from '../../components/data/DataActionItem.vue'
	import xTagModal from '../../components/popover/TagModal.vue'

	import { mapState, mapGetters, mapActions } from 'vuex'
    import { GET_DATA_BY_ID } from '../../store/getters'
    import { DELETE_DATA, DISABLE_DATA, REQUEST_API } from '../../store/actions'

	export default {
		name: 'x-data-action-menu',
        components: {
			xDropdown, 'nested-menu': NestedMenu, 'nested-menu-item': NestedMenuItem,
            xDataActionItem, xTagModal
        },
        props: { module: {required: true}, entities: {required: true} },
        computed: {
            ...mapState({
                dataCount(state) {
                    return state[this.module].count.data
                }
            }),
			...mapGetters({getDataByID: GET_DATA_BY_ID }),
			dataByID() {
                return this.getDataByID(this.module)
            },
            allIDs() {
			    return Object.keys(this.dataByID)
            },
			currentTags() {
                let currentIds = this.entities.include ? this.entities.ids
                    : this.allIDs.filter(id => !this.entities.ids.includes(id))
                if (!currentIds.length) return []
                return currentIds.slice(1).reduce((labels, id) => {
				    return labels.filter(label => this.dataByID[id].labels.includes(label))
                }, this.dataByID[currentIds[0]].labels)
            },
            selectionCount() {
			    if (this.entities.include === undefined || this.entities.include) {
			        return this.entities.ids.length
                }
                return this.dataCount - this.entities.ids.length
            }
        },
        methods: {
            ...mapActions({ disableData: DISABLE_DATA, deleteData: DELETE_DATA, fetchData: REQUEST_API }),
            activate(item) {
            	if (!item || !item.activate) return
                item.activate()
                this.$el.click()
                this.$refs.dropdown.close()
            },
			disableEntities() {
				return this.disableData({ module: this.module, data: this.entities })
			},
            deleteEntities() {
                return this.deleteData({
                    module: this.module, data: this.entities
                }).then(() => this.$emit('done'))
            }
        }
	}
</script>

<style lang="scss">

</style>