<template>
    <scrollable-page title="devices">
        <a slot="pageAction" class="action mt-2" @click="openSaveQuery">Save Query</a>
        <card class="devices-query">
            <template slot="cardContent">
                <!-- Dropdown component for selecting a query --->
                <dropdown-menu animateClass="scale-up right">
                    <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
                    <div slot="dropdownTrigger">
                        <input class="form-control" v-model="queryDropdown.value" @change="extractQuery()"
                               @keyup.enter.stop="executeQuery()" @click.stop="">
                    </div>
                    <!--
                    Content is a form containing appropriate inputs for the fields that are currently selected
                    (in next section). Form content and trigger input's value sync on every change.
                    -->
                    <generic-form slot="dropdownContent" :schema="queryFields" v-model="selectedQuery"
                                  @input="extractValue()" @submit="executeQuery()"></generic-form>
                </dropdown-menu>
                <!-- Button controlling the execution of currently filled query -->
                <a class="btn btn-adjoined" @click="executeQuery()">go</a>
            </template>
        </card>
        <card :title="`devices (${device.deviceList.data.length})`" class="devices-list">
            <div slot="cardActions" class="card-actions">
                <!-- Dropdown for selecting \ creating tags for a currently selected devices --->
                <dropdown-menu animateClass="scale-up right" menuClass="w-md">
                    <i slot="dropdownTrigger" class="icon-tag"></i>
                    <searchable-checklist slot="dropdownContent" slot-scope="props" title="Tag as:"
                                          :items="device.tagList.data" :hasSearch="true" :producesNew="true"
                                          :value="selectedTags" v-on:save="saveTags" :explicitSave="true"
                                          :onDone="props.onDone"></searchable-checklist>
                </dropdown-menu>
                <!-- Dropdown for selecting fields to be presented in table as well as query form -->
                <dropdown-menu animateClass="scale-up right" menuClass="w-lg">
                    <svg-icon slot="dropdownTrigger" name="actions/add_field" height="24" :original="true"></svg-icon>
                    <searchable-checklist slot="dropdownContent" title="Display fields:" :items="visibleFields"
                                          :hasSearch="true" v-model="selectedFields"></searchable-checklist>
                </dropdown-menu>
            </div>
            <div slot="cardContent" class="info-dialog-container">
                <paginated-table :fetching="device.deviceList.fetching" :data="device.deviceList.data"
                                 :error="device.deviceList.error" :fetchData="fetchDevices" v-model="selectedDevices"
                                 :fields="deviceFields" :filter="query.currentQuery"
                                 :actions="[{ handler: executeQuickView, triggerFont: 'icon-eye' }]">

                    <info-dialog v-if="deviceInfoDialog.open" :open="deviceInfoDialog.open" @close="closeQuickView"
                                 :title="deviceInfoDialog.title">
                        <pulse-loader :loading="device.deviceDetails.fetching" color="#26dad2"></pulse-loader>

                        <div v-if="!device.deviceDetails.fetching && Object.keys(device.deviceDetails.data).length">
                            <div class="section-container">
                                <div class="section-header">Adapters</div>
                                <object-list type="image-list" :vertical="true" :names="adapterNameByType"
                                             :data="device.deviceDetails.data['adapters.plugin_name']"></object-list>
                            </div>
                            <div class="section-container">
                                <div class="section-header">Tags</div>
                                <object-list type="tag-list" :vertical="true"
                                             :data="device.deviceDetails.data['tags.tagname']"></object-list>
                            </div>
                            <div class="section-container" v-for="adapter in device.deviceDetails.data['adapters.plugin_name']">
                                <div class="section-header">{{ adapterNameByType[adapter] }} Fields</div>
                                <div>
                                    <tree-view :data="device.deviceDetails.data['adapters.data.raw'][adapter]"
                                               :options="{rootObjectKey: 'raw', maxDepth: 1}"></tree-view>
                                </div>
                            </div>
                        </div>
                    </info-dialog>
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
	import Modal from '../../components/Modal.vue'
	import Card from '../../components/Card.vue'
	import ActionBar from '../../components/ActionBar.vue'
	import GenericForm from '../../components/GenericForm.vue'
	import DropdownMenu from '../../components/DropdownMenu.vue'
	import SearchableChecklist from '../../components/SearchableChecklist.vue'
	import PaginatedTable from '../../components/PaginatedTable.vue'
	import InfoDialog from '../../components/InfoDialog.vue'
	import ObjectList from '../../components/ObjectList.vue'
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
	import { mixin as clickaway } from 'vue-clickaway'
	import '../../components/icons/actions'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
	import {
		FETCH_UNIQUE_FIELDS,
		FETCH_DEVICES,
        FETCH_DEVICE,
		FETCH_TAGS,
		CREATE_DEVICE_TAGS,
		DELETE_DEVICE_TAGS
	} from '../../store/modules/device'
	import { UPDATE_QUERY, SAVE_QUERY, queryToStr, strToQuery } from '../../store/modules/query'
	import { FETCH_ADAPTERS, adapterStaticData } from '../../store/modules/adapter'

	export default {
		name: 'devices-container',
		components: {
			ScrollablePage, Modal, Card, ActionBar, GenericForm, ObjectList,
			DropdownMenu, SearchableChecklist, PaginatedTable, InfoDialog, PulseLoader
		},
		mixins: [clickaway],
		computed: {
			...mapState(['device', 'query']),
			totalFields () {
				let fields = [...this.device.fields.common]
				Object.values(this.device.fields.unique).forEach((currentFields) => {
					fields = fields.concat(currentFields)
				})
				return fields
			},
			visibleFields () {
				return this.totalFields.filter((field) => {
					return !field.hidden
				})
			},
			deviceFields () {
				return this.totalFields.filter((field) => {
					return this.selectedFields.indexOf(field.path) > -1
				})
			},
			queryFields () {
				return this.deviceFields.filter((field) => {
					return field.control !== undefined
				})
			},
            deviceById() {
				return this.device.deviceList.data.reduce(function(map, input) {
					map[input.id] = input
					return map
				}, {})
			},
            adapterNameByType() {
				let nameByType = {}
				Object.keys(adapterStaticData).forEach((adapterId) => {
					nameByType[adapterId] = adapterStaticData[adapterId].name
                })
                return nameByType
            }
		},
		data () {
			return {
				selectedTags: [],
				selectedFields: [],
				selectedDevices: [],
				selectedQuery: {},
				deviceInfoDialog: {
					open: false
				},
				queryDropdown: {
					open: false,
					value: '',
				},
				saveQueryModal: {
					open: false,
					name: ''
				}
			}
		},
		watch: {
			selectedDevices: function(newDevices, oldDevices) {
				if (newDevices.length === 0) { this.selectedTags = [] }
				if (newDevices.length === 1 || !oldDevices.length) {
					let currentDevice = this.deviceById[newDevices[0]]
					if (!currentDevice || !currentDevice['tags.tagname'] || !currentDevice['tags.tagname'].length) {
						return
					}
                    this.selectedTags = currentDevice['tags.tagname']
				}
				if (newDevices.length > 1) {
					if (!this.selectedTags.length) { return }
					newDevices.forEach((deviceId) => {
						let currentDevice = this.deviceById[deviceId]
                        if (!currentDevice || !currentDevice['tags.tagname'] || !currentDevice['tags.tagname'].length) {
                            this.selectedTags = []
                        } else {
                            this.selectedTags = this.selectedTags.filter(function (tag) {
                                return currentDevice['tags.tagname'].indexOf(tag) > -1
                            })
                        }
					})
				}
			}
		},
		created () {
			// TODO Improve backend operation, before returning this to life
			//if (!Object.keys(this.device.fields.unique).length) {
			//	this.fetchFields()
			//}
			this.fetchAdapters()
			this.fetchTags()
			this.selectedQuery = {...this.query.currentQuery}
			this.queryDropdown.value = queryToStr(this.selectedQuery)
			this.selectedFields = this.totalFields.filter(function (field) {
				return field.selected
			}).map(function (field) {
				return field.path
			})
		},
		methods: {
			...mapMutations({
				updateQuery: UPDATE_QUERY
			}),
			...mapActions({
				fetchFields: FETCH_UNIQUE_FIELDS,
				fetchDevices: FETCH_DEVICES,
                fetchDevice: FETCH_DEVICE,
				saveQuery: SAVE_QUERY,
				fetchTags: FETCH_TAGS,
				addDeviceTags: CREATE_DEVICE_TAGS,
                removeDeviceTags: DELETE_DEVICE_TAGS,
				fetchAdapters: FETCH_ADAPTERS
			}),
			extractQuery () {
				this.selectedQuery = strToQuery(this.queryDropdown.value)
			},
			extractValue () {
				this.queryDropdown.value = queryToStr(this.selectedQuery)
			},
			executeQuery () {
				this.closeQuickView()
				this.updateQuery(this.selectedQuery)
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
					filter: this.selectedQuery,
					name: this.saveQueryModal.name,
					callback: () => this.saveQueryModal.open = false
				})
			},
			saveTags (changes) {
				if (!changes ||
                    ((!changes.removed || !changes.removed.length) && (!changes.added || !changes.added.length))) {
					return
                }
                this.addDeviceTags({ devices: this.selectedDevices, tags: changes.added })
				this.removeDeviceTags({ devices: this.selectedDevices, tags: changes.removed })
                this.selectedTags = this.selectedTags.filter((tag) => {
					return changes.removed.indexOf(tag) === -1
				}).concat(changes.added)
			},
			executeQuickView (deviceId) {
				if (!deviceId) { return }
				this.fetchDevice(deviceId)
                this.deviceInfoDialog.title = this.deviceById[deviceId]['adapters.data.name']
                if (!this.deviceInfoDialog.title) {
					this.deviceInfoDialog.title = this.deviceById[deviceId]['adapters.data.hostname']
                }
				this.deviceInfoDialog.open = true
			},
            closeQuickView() {
				this.deviceInfoDialog.open = false
            },
            removePrefix(value) {
				if (!value) { return '' }
				return value.split('.').splice(1).join('.')
            }
		}
	}
</script>


<style lang="scss">
    @import '../../scss/config';

    .devices-query {
        .card-body {
            display: flex;
            > .dropdown {
                flex: 1 0 auto;
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
                > .dropdown-toggle {
                    padding-right: 0;
                    padding-left: 0;
                    .form-control {
                        border-top-right-radius: 0;
                        border-bottom-right-radius: 0;
                        margin: -1px;
                        border-right: 0;
                    }
                }
            }
            > .btn {
                line-height: 28px;
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
            }
        }
    }

    .devices-list {
        .card-actions {
            .svg-icon {
                margin-right: 24px;
                margin-top: 4px;
                padding: 2px;
                .svg-stroke {
                    stroke: $color-text-title;
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
            .svg-icon, i {
                margin-right: 30px;
            }
        }
    }

</style>