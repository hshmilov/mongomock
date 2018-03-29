<template>
    <x-page title="devices">
        <a slot="pageAction" @click="openSaveModal(confirmSaveQuery)">Save Query</a>
        <x-data-query module="device" :schema="coloumnSelectionFields" :selected="selectedFields"/>

        <x-data-table module="device" :fields="tableFields" id-field="internal_axon_id"
                      v-model="selectedDevices" @click-row="configDevice" title="Devices">
            <template slot="tableActions">
                <!-- Available actions for performing on currently selected group of devices --->
                <devices-actions-container v-show="selectedDevices && selectedDevices.length" :devices="selectedDevices"/>

                <triggerable-dropdown :arrow="false" align="right">
                    <div slot="dropdownTrigger" class="link">View</div>
                    <nested-menu slot="dropdownContent">
                        <nested-menu-item title="Save" @click="openSaveModal(confirmSaveView)" />
                        <nested-menu-item title="Load">
                            <dynamic-popover size="sm" left="-236" top="0">
                                <nested-menu class="inner" v-if="tableViews && tableViews.length">
                                    <nested-menu-item v-for="{name, view} in tableViews" :key="name" :title="name"
                                                      @click="updateModuleView(view)"/>
                                </nested-menu>
                                <div v-else>No saved views</div>
                            </dynamic-popover>
                        </nested-menu-item>
                    </nested-menu>
                </triggerable-dropdown>

                <!-- Dropdown for selecting fields to be presented in table, including adapter hierarchy -->
                <x-graded-multi-select placeholder="Add Columns" :options="coloumnSelectionFields" v-model="selectedFields"/>
            </template>
        </x-data-table>
        <modal v-if="saveModal.open" @close="saveModal.open = false" approveText="save" @confirm="saveModal.handleConfirm">
            <div slot="body" class="form-group">
                <label class="form-label" for="saveName">Save as:</label>
                <input class="form-control" v-model="saveModal.name" id="saveName" @keyup.enter="saveModal.handleConfirm">
            </div>
        </modal>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import Modal from '../../components/popover/Modal.vue'
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
	import DevicesActionsContainer from './DevicesActionsContainer.vue'
	import xDataQuery from '../../components/data/DataQuery.vue'
    import xGradedMultiSelect from '../../components/GradedMultiSelect.vue'
    import xDataTable from '../../components/tables/DataTable.vue'
	import NestedMenu from '../../components/menus/NestedMenu.vue'
	import NestedMenuItem from '../../components/menus/NestedMenuItem.vue'
	import DynamicPopover from '../../components/popover/DynamicPopover.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
	import { FETCH_DEVICE, FETCH_LABELS } from '../../store/modules/device'
	import { FETCH_ADAPTERS, adapterStaticData } from '../../store/modules/adapter'
    import { FETCH_SETTINGS } from '../../store/modules/settings'
	import {
		FETCH_DATA_VIEWS, SAVE_DATA_VIEW, FETCH_DATA_FIELDS, SAVE_DATA_QUERY
	} from '../../store/actions'
	import { UPDATE_DATA_VIEW } from '../../store/mutations'

	export default {
		name: 'devices-container',
		components: {
			xPage, xDataQuery, DevicesActionsContainer, DynamicPopover,
			Modal, TriggerableDropdown, xGradedMultiSelect, xDataTable, NestedMenu, NestedMenuItem
		},
		computed: {
			...mapState(['device', 'adapter', 'settings']),
			selectedFields: {
				get() {
					return this.device.data.view.fields
				},
				set(fieldList) {
                    this.updateModuleView({fields: fieldList})
				}
			},
            deviceFields () {
				return this.device.data.fields.data
            },
			genericFlatSchema () {
				if (!this.deviceFields.generic) return []
				return [
					{
						name: 'adapters', title: 'Adapters', type: 'array', items: {type: 'string', format: 'logo',
                            enum: Object.keys(this.specificFlatSchema).map((name) => {
								return {name, title: adapterStaticData[name].name}
                            })
						}
					}, ...this.deviceFields.generic,
					{
						name: 'labels', title: 'Tags', type: 'array', items: {type: 'string', format: 'tag'}
					}
                ]
			},
			specificFlatSchema () {
				if (!this.deviceFields.specific) return {}
                let registeredAdapters = this.adapter.adapterList.data.map((adapter) => adapter.plugin_name.logo)

				return registeredAdapters.reduce((map, name) => {
					if (this.deviceFields.specific[name] && this.deviceFields.specific[name].length) {
					    map[name] = this.deviceFields.specific[name]
                    }
                    return map
				}, {})
			},
            coloumnSelectionFields() {
				if (!this.genericFlatSchema.length) return []

				return [
					{
						title: 'Generic', fields: this.genericFlatSchema
					},
					...Object.keys(this.specificFlatSchema).map((name) => {
						let title = adapterStaticData[name] ? adapterStaticData[name].name : name
						return { title, fields: this.specificFlatSchema[name] }
					})
                ]
            },
			tableFields () {
				if (!this.genericFlatSchema.length) return []
				return this.genericFlatSchema.filter((field) => {
                    return !(field.type === 'array' && (Array.isArray(field.items) || field.items.type === 'array'))
				}).concat(Object.keys(this.specificFlatSchema).reduce((list, name) => {
					if (!this.specificFlatSchema[name]) return list
					list = [...list, ...this.specificFlatSchema[name].map((field) => {
						if (this.settings.data.singleAdapter) return field
						return { ...field, logo: name}
                    })]
					return list
				}, []))
			},
            tableViews () {
				return this.device.data.views.data
            }
		},
		data () {
			return {
				selectedDevices: [],
				saveModal: {
					open: false,
					name: '',
                    handleConfirm: null
				}
			}
		},
		methods: {
			...mapMutations({
				updateView: UPDATE_DATA_VIEW,
			}),
			...mapActions({
				fetchDataFields: FETCH_DATA_FIELDS,
				fetchDevice: FETCH_DEVICE,
				saveQuery: SAVE_DATA_QUERY,
				fetchLabels: FETCH_LABELS,
				fetchAdapters: FETCH_ADAPTERS,
                fetchDataViews: FETCH_DATA_VIEWS,
                saveDataView: SAVE_DATA_VIEW,
                fetchSettings: FETCH_SETTINGS
			}),
            openSaveModal(confirmHandler) {
				this.saveModal.open = true
                this.saveModal.handleConfirm = confirmHandler
            },
			confirmSaveQuery () {
				if (!this.saveModal.name) return

				this.saveQuery({
                    module: 'device',
					name: this.saveModal.name
				}).then(() => this.saveModal.open = false)
			},
            confirmSaveView () {
				if (!this.saveModal.name) return

                this.saveDataView({
                    module: 'device', name: this.saveModal.name
                }).then(() => this.saveModal.open = false)
            },
			configDevice (deviceId) {
				if (this.selectedDevices && this.selectedDevices.length) {
					return
				}
				this.fetchDevice(deviceId)
				this.$router.push({path: `device/${deviceId}`})
			},
			updateModuleView(view) {
				this.updateView({module: 'device', view})
			},
		},
		created () {
			this.fetchAdapters()
            this.fetchSettings()
            this.fetchDataViews({module: 'device'})
            this.fetchDataFields({module: 'device'})
            if (!this.device.labelList.data || !this.device.labelList.data.length) {
				this.fetchLabels()
			}
		}
	}
</script>


<style lang="scss">

</style>