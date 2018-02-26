<template>
    <scrollable-page title="devices">
        <a slot="pageAction" class="action mt-2" @click="openSaveQuery">Save Query</a>
        <card class="devices-query">
            <devices-filter-container slot="cardContent" :schema="filterFields" v-model="queryFilter"
                                      :selected="selectedFields" @submit="executeQuery"></devices-filter-container>
        </card>
        <card :title="`devices (${device.deviceCount.data})`" class="devices-list">
            <div slot="cardActions" class="card-actions">

                <!-- Available actions for performing on currently selected group of devices --->
                <devices-actions-container v-show="selectedDevices && selectedDevices.length"
                                           :devices="selectedDevices"></devices-actions-container>

                <!-- Dropdown for selecting fields to be presented in table, including adapter hierarchy -->
                <x-graded-multi-select placeholder="Add Columns" :options="coloumnSelectionFields"
                                       v-model="selectedFields"></x-graded-multi-select>
            </div>
            <div slot="cardContent">
                <x-schema-table :fetching="device.deviceList.fetching" :data="device.deviceList.data"
                                :error="device.deviceList.error" :fetchData="fetchDevices" v-model="selectedDevices"
                                :fields="selectedTableFields" :filter="queryFilter" @click-row="configDevice"
                                :selected-page="device.deviceSelectedPage" @change-page="selectPage"
                                id-field="internal_axon_id">
                </x-schema-table>
            </div>
        </card>
        <modal v-if="saveQueryModal.open" @close="saveQueryModal.open = false" approveText="save"
               @confirm="approveSaveQuery()">
            <div slot="body" class="form-group">
                <label class="form-label" for="saveQueryName">Save Query as:</label>
                <input class="form-control" v-model="saveQueryModal.name" id="saveQueryName"
                       @keyup.enter="approveSaveQuery()">
            </div>
        </modal>
    </scrollable-page>
</template>

<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
	import Modal from '../../components/popover/Modal.vue'
	import Card from '../../components/Card.vue'
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
	import xSchemaTable from '../../components/data/SchemaTable.vue'
	import DevicesActionsContainer from './DevicesActionsContainer.vue'
	import DevicesFilterContainer from './DevicesFilterContainer.vue'
    import xGradedMultiSelect from '../../components/GradedMultiSelect.vue'

	import '../../components/icons/action'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
	import {
		FETCH_DEVICES,
		FETCH_DEVICE,
		FETCH_LABELS,
		SELECT_DEVICE_PAGE,
        SELECT_DEVICE_FIELDS,
		FETCH_DEVICE_FIELDS
	} from '../../store/modules/device'
	import { UPDATE_QUERY, SAVE_QUERY, FETCH_SAVED_QUERIES } from '../../store/modules/query'
	import { FETCH_ADAPTERS, adapterStaticData } from '../../store/modules/adapter'

	export default {
		name: 'devices-container',
		components: {
			DevicesFilterContainer, DevicesActionsContainer, ScrollablePage, Card,
			Modal, TriggerableDropdown, xGradedMultiSelect, xSchemaTable
		},
		computed: {
			...mapState(['device', 'query', 'adapter']),
			queryFilter: {
				get () {
					return this.query.newQuery.filter
				},
				set (newFilter) {
					this.updateQuery(newFilter)
				}
			},
			selectedFields: {
				get() {
					return this.device.deviceSelectedFields
				},
				set(fieldList) {
                    this.selectFields(fieldList)
				}
			},
			genericFlatSchema () {
				if (!this.device.deviceFields.data.generic) return []
				return [
					{
						name: 'adapters', title: 'Adapters', type: 'array',
						items: {type: 'string', format: 'logo',
                            enum: Object.keys(adapterStaticData).map((name) => {
								return {name, title: adapterStaticData[name].name}
                            })
						}
					},
                    ...this.flattenSchema(this.device.deviceFields.data.generic),
					{
						name: 'labels', title: 'Tags', type: 'array',
						items: {type: 'string', format: 'tag'}
					}
                ]
			},
			specificFlatSchema () {
				if (!this.device.deviceFields.data.specific) return []
                let registeredAdapters = new Set(this.adapter.adapterList.data.map((adapter) => adapter.plugin_name.logo))

				return Object.keys(this.device.deviceFields.data.specific).reduce((map, pluginName) => {
					if (!registeredAdapters.has(pluginName)) return map

					let pluginFlatSchema = this.flattenSchema(this.device.deviceFields.data.specific[pluginName])
					if (!pluginFlatSchema.length) return map
                    let title = adapterStaticData[pluginName] ? adapterStaticData[pluginName].name : pluginName
					map[title] = pluginFlatSchema
                    return map
				}, {})
			},
            coloumnSelectionFields() {
				if (!this.genericFlatSchema.length) return []

				return [
					{
						title: 'Generic', fields: this.genericFlatSchema
					},
					...Object.keys(this.specificFlatSchema).map((title) => {
						return { title, fields: this.specificFlatSchema[title] }
					})
                ]
            },
			tableFields () {
				if (!this.genericFlatSchema.length) return []
				return this.genericFlatSchema.filter((field) => {
                    return !(field.type === 'array' && (Array.isArray(field.items) || field.items.type === 'array'))
				}).concat(Object.keys(this.specificFlatSchema).reduce((merged, title) => {
					merged = [...merged, ...this.specificFlatSchema[title].map((field) => {
						return { ...field, title: `${title} ${field.title}`}
                    })]
					return merged
				}, []))
			},
            selectedTableFields() {
				let existing = new Set()
				return this.tableFields.filter((field) => {
					if (existing.has(field.name)) return false
					existing.add(field.name)
					return field.name && this.selectedFields.includes(field.name)
				})
            },
			filterFields () {
				if (!this.genericFlatSchema.length) return []

				return [
					{
						name: 'saved_query', title: 'Saved Query', type: 'string', format: 'predefined',
						enum: this.query.savedQueries.data.map((query) => {
							return {name: query.filter, title: query.name}
						})
					},
                    ...this.coloumnSelectionFields
				]
			}
		},
		data () {
			return {
				selectedDevices: [],
				saveQueryModal: {
					open: false,
					name: ''
				}
			}
		},
		methods: {
			...mapMutations({
				updateQuery: UPDATE_QUERY,
				selectPage: SELECT_DEVICE_PAGE,
                selectFields: SELECT_DEVICE_FIELDS
			}),
			...mapActions({
				fetchDevices: FETCH_DEVICES,
				fetchDeviceFields: FETCH_DEVICE_FIELDS,
				fetchDevice: FETCH_DEVICE,
				saveQuery: SAVE_QUERY,
				fetchLabels: FETCH_LABELS,
				fetchAdapters: FETCH_ADAPTERS,
				fetchSavedQueries: FETCH_SAVED_QUERIES
			}),
			executeQuery () {
				this.updateQuery(this.queryFilter)
				this.fetchDevices({
					filter: this.queryFilter, skip: 0,
					fields: this.selectedTableFields.map((field) => field.name)
				})
				this.selectPage(0)
				this.$parent.$el.click()
			},
			openSaveQuery () {
				this.saveQueryModal.open = true
			},
			approveSaveQuery () {
				if (!this.saveQueryModal.name) {
					return
				}
				this.saveQuery({
					filter: this.queryFilter,
					name: this.saveQueryModal.name
				}).then(() => {
					this.saveQueryModal.open = false
				})
			},
			configDevice (deviceId) {
				if (this.selectedDevices && this.selectedDevices.length) {
					return
				}
				this.fetchDevice(deviceId)
				this.$router.push({path: `device/${deviceId}`})
			},
			flattenSchema (schema, name = '') {
				/*
				    Recursion over schema to extract a flat map from field path to its schema
				 */
				if (schema.name) {
					name = name ? `${name}.${schema.name}` : schema.name
				}
				if (schema.type === 'array' && schema.items) {
					if (!Array.isArray(schema.items)) {
						let childSchema = {...schema.items}
						if (schema.items.type !== 'array') {
							if (!schema.title) return []
							return [{...schema, name}]
						}
						if (schema.title) {
							childSchema.title = childSchema.title ? `${schema.title} ${childSchema.title}` : schema.title
						}
						return this.flattenSchema(childSchema, name)
					}
					let children = []
					schema.items.forEach((item) => {
						children = children.concat(this.flattenSchema({...item}, name))
					})
					return children
				}
				if (schema.type === 'object' && schema.properties) {
					let children = []
					Object.keys(schema.properties).forEach((key) => {
						children = children.concat(this.flattenSchema({...schema.properties[key], name: key}, name))
					})
					return children
				}
				if (!schema.title) return []
				return [{...schema, name}]
			}
		},
		created () {
			this.fetchAdapters()
			if (!this.device.deviceFields.data || !this.device.deviceFields.data.generic) {
				this.fetchDeviceFields()
			}
			if (!this.query.savedQueries.data || !this.query.savedQueries.data.length) {
				this.fetchSavedQueries()
			}
            if (!this.device.labelList.data || !this.device.labelList.data.length) {
				this.fetchLabels()
			}

			this.interval = setInterval(function () {
				this.fetchDevices({
					filter: this.queryFilter, skip: 0,
					fields: this.selectedTableFields.map((field) => field.name)
				})
			}.bind(this), 3000);
		},
		beforeDestroy() {
			clearInterval(this.interval);
		}
	}
</script>


<style lang="scss">
    @import '../../scss/config';

    .devices-list {
        .card-actions {
            .svg-icon {
                margin-right: 24px;
                margin-top: 4px;
                padding: 2px;
                .svg-stroke {
                    stroke: $color-text-main;
                    stroke-width: 20px;
                }
            }
        }
        .section-container {
            margin-bottom: 24px;
            &:last-of-type {
                margin-bottom: 0;
            }
            .section-header {
                border-bottom: 1px solid $border-color;
            }
        }
        .dropdown-toggle {
            .svg-icon, i, .link {
                margin-right: 30px;
            }
            .link {
                vertical-align: middle;
                line-height: 30px;
                &:hover {
                    color: $color-text-link;
                }
            }
        }
    }

</style>