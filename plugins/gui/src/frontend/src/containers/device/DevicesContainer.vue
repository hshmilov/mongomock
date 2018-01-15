<template>
    <scrollable-page title="devices">
        <a slot="pageAction" class="action mt-2" @click="openSaveQuery">Save Query</a>
        <card class="devices-query">
            <template slot="cardContent">
                <i class="icon-help trigger-help" @click="openHelpTooltip = !openHelpTooltip"></i>
                <div v-show="openHelpTooltip" class="help">
                    <div>An advanced query is a recursive expression defined as:</div>
                    <div>EXPR: [ not ] &lt;field path&gt; COMP &lt;required value&gt; [ LOGIC EXPR ]</div>
                    <div>COMP:  == | != | > | < | >= | <= | in</div>
                    <div>LOGIC: and | or</div>
                    <div>The value can be a primitive, like a string or a number, or a function like:</div>
                    <div>regex(&lt;regular expression&gt;)</div>
                </div>

                <!-- Dropdown component for selecting a query --->
                <dropdown-menu animateClass="scale-up right">
                    <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
                    <div slot="dropdownTrigger" class="input-container">
                        <input class="form-control" v-model="selectedQuery" @keyup.enter.stop="executeQuery"
                               @click.stop="">
                    </div>
                    <!--
                    Content is a form containing appropriate inputs for the fields that are currently selected
                    (in next section). Form content and trigger input's value sync on every change.
                    -->
                    <generic-form slot="dropdownContent" :schema="queryFields" v-model="queryDropdown.value"
                                  @input="extractValue" @submit="executeQuery" :condensed="true"></generic-form>
                </dropdown-menu>
                <!-- Button controlling the execution of currently filled query -->
                <a class="btn btn-adjoined" @click="executeQuery">go</a>
            </template>
        </card>
        <card :title="`devices (${device.deviceCount.data})`" class="devices-list">
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
                    <svg-icon slot="dropdownTrigger" name="action/add_field" height="24" :original="true"></svg-icon>
                    <searchable-checklist slot="dropdownContent" title="Display fields:" :items="visibleFields"
                                          :hasSearch="true" v-model="selectedFields"></searchable-checklist>
                </dropdown-menu>
            </div>
            <div slot="cardContent" class="info-dialog-container">
                <paginated-table :fetching="device.deviceList.fetching" :data="device.deviceList.data"
                                 :error="device.deviceList.error" :fetchData="fetchDevices" v-model="selectedDevices"
                                 :fields="deviceFields" :filter="query.currentQuery" @click-row="configDevice">

                    <!--info-dialog v-if="deviceInfoDialog.open" :open="deviceInfoDialog.open" @close="closeQuickView"
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
                    </info-dialog-->
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
	import '../../components/icons/action'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
	import {
		FETCH_UNIQUE_FIELDS,
		FETCH_DEVICES,
        FETCH_DEVICES_COUNT,
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
            },
            deviceActions() {
				return [{ handler: this.executeQuickView, triggerFont: 'icon-eye' },
                    {handler: this.configDevice, triggerIcon: 'action/edit'}]
            }
		},
		data () {
			return {
				selectedTags: [],
				selectedFields: [],
				selectedDevices: [],
				selectedQuery: "",
				deviceInfoDialog: {
					open: false
				},
				queryDropdown: {
					open: false,
					value: {},
				},
				saveQueryModal: {
					open: false,
					name: ''
				},
                openHelpTooltip: false
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
			this.selectedQuery = this.query.currentQuery
			this.fetchDevicesCount({ filter: this.selectedQuery })
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
                fetchDevicesCount: FETCH_DEVICES_COUNT,
                fetchDevice: FETCH_DEVICE,
				saveQuery: SAVE_QUERY,
				fetchTags: FETCH_TAGS,
				addDeviceTags: CREATE_DEVICE_TAGS,
                removeDeviceTags: DELETE_DEVICE_TAGS,
				fetchAdapters: FETCH_ADAPTERS
			}),
			extractValue () {
				this.selectedQuery = queryToStr(this.queryDropdown.value)
			},
			executeQuery () {
				this.closeQuickView()
				this.updateQuery(this.selectedQuery)
                this.fetchDevicesCount({ filter: this.selectedQuery })
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
					name: this.saveQueryModal.name
				}).then(() => {
					this.saveQueryModal.open = false
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
            },
            configDevice(deviceId) {
				this.fetchDevice(deviceId)
				this.$router.push({path: `device/${deviceId}`})
            }
		}
	}
</script>


<style lang="scss">
    @import '../../scss/config';

    .devices-query {
        .card-body {
            display: flex;
            .trigger-help {
                vertical-align: middle;
                font-size: 24px;
                line-height: 36px;
                margin-right: 4px;
                cursor: pointer;
            }
            .help {
                position: absolute;
                z-index: 10;
                top: 50px;
                background-color: white;
                border-radius: 4px;
                border: 1px solid $border-color;
                padding: 8px;
                font-size: 12px;
                box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
                -webkit-box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
                -moz-box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
            }
            > .dropdown {
                flex: 1 0 auto;
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
                > .dropdown-toggle {
                    padding-right: 0;
                    padding-left: 0;
                    .input-container {
                        padding-right: 30px;
                        border-top-left-radius: 4px;
                        border-bottom-left-radius: 4px;
                        border: 1px solid rgba(0,0,0,.15);
                        border-right: 0;
                        .form-control {
                            border: 0;
                        }
                    }
                    &:after {
                        top: 4px;
                    }
                }
            }
            > .btn {
                line-height: 32px;
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
            .svg-icon, i {
                margin-right: 30px;
            }
        }
    }

</style>