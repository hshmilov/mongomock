<template>
    <scrollable-page title="devices">
        <a slot="pageAction" class="action mt-2" @click="openSaveQuery">Save Query</a>
        <card class="devices-query">
            <devices-filter-container slot="cardContent" :schema="deviceFlatSchema" v-model="queryFilter"
                                      @submit="executeQuery"></devices-filter-container>
        </card>
        <card :title="`devices (${device.deviceCount.data})`" class="devices-list">
            <div slot="cardActions" class="card-actions">

                <!-- Available actions for performing on currently selected group of devices --->
                <devices-actions-container v-show="selectedDevices && selectedDevices.length"
                                           :devices="selectedDevices"></devices-actions-container>

                <!-- Dropdown for selecting fields to be presented in table as well as query form -->
                <triggerable-dropdown size="lg" align="right">
                    <div slot="dropdownTrigger" class="link">Add Columns</div>
                    <searchable-checklist slot="dropdownContent" title="Display fields:" :items="visibleFields"
                                          :searchable="true" v-model="selectedFields"></searchable-checklist>
                </triggerable-dropdown>
            </div>
            <div slot="cardContent">
                <paginated-table :fetching="device.deviceList.fetching" :data="device.deviceList.data"
                                 :error="device.deviceList.error" :fetchData="fetchDevices" v-model="selectedDevices"
                                 :fields="deviceFields" :filter="selectedFilter" @click-row="configDevice"
                                 :selected-page="device.deviceSelectedPage" @change-page="selectPage">
                </paginated-table>
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
	import SearchableChecklist from '../../components/SearchableChecklist.vue'
	import PaginatedTable from '../../components/tables/PaginatedTable.vue'
    import DevicesActionsContainer from './DevicesActionsContainer.vue'
    import DevicesFilterContainer from './DevicesFilterContainer.vue'

	import '../../components/icons/action'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
	import {
		FETCH_UNIQUE_FIELDS,
		FETCH_DEVICES,
        FETCH_DEVICES_COUNT,
        FETCH_DEVICE,
		FETCH_TAGS,
        SELECT_DEVICE_PAGE,
        UPDATE_DEVICE_FILTER
	} from '../../store/modules/device'
	import { UPDATE_QUERY, SAVE_QUERY, FETCH_SAVED_QUERIES } from '../../store/modules/query'
	import { FETCH_ADAPTERS, adapterStaticData } from '../../store/modules/adapter'

	export default {
		name: 'devices-container',
		components: {
			DevicesFilterContainer, DevicesActionsContainer, ScrollablePage, Card,
            Modal, TriggerableDropdown, SearchableChecklist, PaginatedTable
		},
		computed: {
			...mapState(['device', 'query']),
			totalFields () {
				return [...this.device.fields.common]
			},
			visibleFields () {
				return this.totalFields.filter((field) => {
					return !field.hidden
				})
			},
			deviceFields () {
				return this.totalFields.filter((field) => {
					return this.selectedFields.includes(field.path)
				})
			},
            queryFilter: {
				get() {
					return this.query.newQuery.filter
                },
                set(newFilter) {
                    this.updateQuery(newFilter)
                }
            },
            deviceSchema () {
				return {
					type: 'array',
                    items: [
                        {
                        	name: 'saved_query',
                            title: 'Saved Query',
                            type: 'string',
                            format: 'predefined',
                            enum: this.query.savedQueries.data.map((query) => {
                        		return {name: query.filter, title: query.name}
                            })
                        },
                        {
                        	name: 'adapters',
                            title: 'Adapters',
                            type: 'array',
                            items: {
                        		type: 'array',
                        		items: [
                                {
                                	name: 'plugin_name',
                                    title: 'Adapter Name',
                                    type: 'string',
                                    enum: Object.keys(adapterStaticData).map((name) => {
                                		return { name, title: adapterStaticData[name].name}
                                    })
                                },
                                this.device.deviceFields.data
                            ]}
                        },
                        {
                        	name: 'tags',
							title: 'Tags',
							type: 'array',
                            items: {
                        		type: 'array',
                                items: [
                                    {
                                    	name: 'tagname',
                                        title: 'Tag Name',
                                        type: 'string'
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            deviceFlatSchema() {
                return this.flattenSchema(this.deviceSchema)
            }
		},
		data () {
			return {
				selectedFilter: this.queryFilter,
				selectedFields: [],
				selectedDevices: [],
				saveQueryModal: {
					open: false,
					name: ''
				}
			}
		},
		mounted () {
            if (!this.query.savedQueries.data || !this.query.savedQueries.data.length) {
                this.fetchSavedQueries()
            }
			this.fetchAdapters()
			this.fetchTags()
			this.fetchDevicesCount({ filter: this.queryFilter })
			this.selectedFields = this.totalFields.filter(function (field) {
				return field.selected
			}).map(function (field) {
				return field.path
			})
		},
		methods: {
			...mapMutations({
				updateQuery: UPDATE_QUERY,
                selectPage: SELECT_DEVICE_PAGE
			}),
			...mapActions({
				fetchFields: FETCH_UNIQUE_FIELDS,
				fetchDevices: FETCH_DEVICES,
                fetchDevicesCount: FETCH_DEVICES_COUNT,
                fetchDevice: FETCH_DEVICE,
				saveQuery: SAVE_QUERY,
				fetchTags: FETCH_TAGS,
				fetchAdapters: FETCH_ADAPTERS,
                fetchSavedQueries: FETCH_SAVED_QUERIES
			}),
			executeQuery () {
				this.selectedFilter = this.queryFilter
				this.updateQuery(this.queryFilter)
                this.fetchDevicesCount({ filter: this.queryFilter })
                this.fetchDevices({ filter: this.queryFilter, skip: 0})
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
            configDevice(deviceId) {
				if (this.selectedDevices && this.selectedDevices.length) {
					return
                }
				this.fetchDevice(deviceId)
				this.$router.push({path: `device/${deviceId}`})
            },
			flattenSchema (schema, name='') {
				/*
				    Recursion over schema to extract a flat map from field path to its schema
				 */
				if (schema.name) {
					name = name? `${name}.${schema.name}` : schema.name
				}
				if (schema.type === 'array' && schema.items) {
					if (!Array.isArray(schema.items)) {
						let childSchema = { ...schema.items}
						if (schema.title) {
							childSchema.title = childSchema.title? `${schema.title} ${childSchema.title}`: schema.title
						}
						let children = this.flattenSchema(childSchema, name)
						if (schema.items.type !== 'array') {
							return children
						}
						return [ {...schema, name}, ...children ]
					}
					let children = []
					schema.items.forEach((item) => {
						children = children.concat(this.flattenSchema({ ...item }, name))
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
				return [{ ...schema, name}]
			}
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