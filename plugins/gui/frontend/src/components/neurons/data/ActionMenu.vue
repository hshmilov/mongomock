<template>
    <div>
        <x-dropdown size="sm" align="right" :arrow="false" ref="dropdown">
            <button slot="trigger" class="x-btn link">Actions</button>
            <x-menu slot="content">
                <x-menu-item v-for="item in $children" v-if="item.title" :key="item.title"
                                  :title="item.title" @click="activate(item)"/>
            </x-menu>
        </x-dropdown>
        <x-tag-modal title="Tag..." :module="module" :entities="entities" :value="currentTags" />
        <x-action-menu-item title="Delete..." :handle-save="deleteEntities" :message="`Deleted ${module}`"
                            action-text="Delete">
            <div class="warn-delete">You are about to delete {{ selectionCount }} {{module}}.</div>
            <div>These {{module}} could reappear in further scans if they are not removed or detached.</div>
            <div>Are you sure you want to delete these {{module}}?</div>
        </x-action-menu-item>
        <slot></slot>
        <x-action-menu-item :title="`Add custom data...`" :handle-save="saveFields" :message="`Custom data saved`"
                            action-text="Save">
            <x-custom-fields :module="module" v-model="customAdapterData" :fields="fields" />
        </x-action-menu-item>
    </div>
</template>

<script>
	import xDropdown from '../../axons/popover/Dropdown.vue'
	import xMenu from '../../axons/menus/Menu.vue'
	import xMenuItem from '../../axons/menus/MenuItem.vue'
    import xActionMenuItem from './ActionMenuItem.vue'
	import xTagModal from '../popover/TagModal.vue'
    import xCustomFields from '../../networks/entities/CustomFields.vue'

	import { mapState, mapGetters, mapActions } from 'vuex'
    import { GET_DATA_BY_ID } from '../../../store/getters'
    import { DELETE_DATA, DISABLE_DATA, SAVE_CUSTOM_DATA } from '../../../store/actions'

	export default {
		name: 'x-action-menu',
        components: {
			xDropdown, 'x-menu': xMenu, 'x-menu-item': xMenuItem,
            xActionMenuItem, xTagModal, xCustomFields
        },
        props: { module: {required: true}, entities: {required: true} },
        computed: {
            ...mapState({
                dataCount(state) {
                    return state[this.module].count.data
                },
                fields(state) {
                    let fields = state[this.module].fields.data
                    if (!fields) return []
                    if (!fields.specific) return fields.generic
                    return fields.specific.gui || fields.generic
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
                    if (!this.dataByID[id].labels) return []
				    return labels.filter(label => this.dataByID[id].labels.includes(label))
                }, this.dataByID[currentIds[0]].labels || [])
            },
            selectionCount() {
			    if (this.entities.include === undefined || this.entities.include) {
			        return this.entities.ids.length
                }
                return this.dataCount - this.entities.ids.length
            }
        },
        data() {
		    return {
                customAdapterData: { id: 'unique' }
            }
        },
        methods: {
            ...mapActions({ disableData: DISABLE_DATA, deleteData: DELETE_DATA, saveCustomData: SAVE_CUSTOM_DATA }),
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
            },
            saveFields() {
                return this.saveCustomData({
                    module: this.module, data: {
                        selection: this.entities, data: this.customAdapterData
                    }
                }).then(() => this.$emit('done'))
            }
        }
	}
</script>

<style lang="scss">

</style>