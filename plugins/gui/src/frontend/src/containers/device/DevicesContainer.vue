<template>
    <scrollable-page title="devices">
        <card title="query" class="devices-query">
            <span slot="cardActions">
                <!-- Actions for the header of the query card and apply to currently filled query -->
                <action-bar :actions="[
                    { title: 'Save Query', handler: openSaveQuery }
                ]"></action-bar>
            </span>
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
                <a class="btn" @click="executeQuery()">go</a>
            </template>
        </card>
        <card :title="`devices (${device.deviceList.data.length})`" class="devices-list">
            <div slot="cardActions" class="card-actions">
                <!-- Dropdown for selecting \ creating tags for a currently selected devices --->
                <dropdown-menu animateClass="scale-up right">
                    <i slot="dropdownTrigger" class="icon-tag"></i>
                    <searchable-checklist slot="dropdownContent" slot-scope="props" title="Tag as:"
                                          :items="device.tagList.data" :hasSearch="true" :producesNew="true"
                                          v-model="selectedTags" v-on:save="saveTags()" :explicitSave="true"
                                          :onDone="props.onDone"></searchable-checklist>
                </dropdown-menu>
                <!-- Dropdown for selecting fields to be presented in table as well as query form -->
                <dropdown-menu animateClass="scale-up right" menuClass="w-md">
                    <svg-icon slot="dropdownTrigger" name="actions/add_field" height="24" :original="true"></svg-icon>
                    <searchable-checklist slot="dropdownContent" title="Display fields:" :items="totalFields"
                                          :hasSearch="true" v-model="selectedFields"></searchable-checklist>
                </dropdown-menu>
            </div>
            <div slot="cardContent" v-on-clickaway="closeQuickView">
                <paginated-table :fetching="device.deviceList.fetching" :data="device.deviceList.data"
                                 :error="device.deviceList.error" :fields="deviceFields" :fetchData="fetchDevices"
                                 v-model="selectedDevices" :filter="query.currentQuery"
                                 :actions="[{ handler: executeQuickView, triggerFont: 'icon-eye'}]"></paginated-table>
                <info-dialog :open="infoDialogOpen" title="Device Quick View" :closeDialog="closeQuickView.bind(this)">
                    <div class="d-flex flex-row justify-content-between p-3">
                        <div>{{ device.deviceDetails.name }}</div>
                        <div>{{ device.deviceDetails.IP }}</div>
                    </div>
                    <div v-if="device.deviceDetails.data.adapters && device.deviceDetails.data.adapters.length"
                         class="d-flex flex-column justify-content-between p-3">
                        <div>Adapters</div>
                        <hr class="title-separator">
                        <object-list :data="device.deviceDetails.data.adapters" :vertical="true"
                                     :names="device.adapterNames"></object-list>
                    </div>
                    <div v-if="device.deviceDetails.data.tags && device.deviceDetails.data.tags.length"
                         class="d-flex flex-column justify-content-between align-items-start p-3">
                        <div>Tags</div>
                        <hr class="title-separator">
                        <object-list :data="device.deviceDetails.data.tags" :vertical="true"></object-list>
                    </div>
                </info-dialog>
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
	import { mixin as clickaway } from 'vue-clickaway'
    import '../../components/icons/actions'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
	import { FETCH_UNIQUE_FIELDS, FETCH_DEVICES, FETCH_DEVICE, FETCH_TAGS, SAVE_DEVICE_TAGS } from '../../store/modules/device'
	import { UPDATE_QUERY, SAVE_QUERY, queryToStr, strToQuery } from '../../store/modules/query'

	export default {
		name: 'devices-container',
		components: {
			ScrollablePage, Modal, Card, ActionBar, GenericForm, ObjectList,
			DropdownMenu, SearchableChecklist, PaginatedTable, InfoDialog
		},
		mixins: [clickaway],
		computed: {
			...mapState(['device', 'query']),
            totalFields() {
				return [ ...this.device.fields.common, ...this.device.fields.unique ]
            },
            deviceFields() {
				return this.totalFields.filter((field) => {
					return this.selectedFields.indexOf(field.path) > -1
				})
			},
			queryFields () {
				return this.deviceFields.filter((field) => {
					return field.control !== undefined
				})
			}
		},
		data () {
			return {
				selectedTags: [],
				selectedFields: [],
				selectedDevices: [],
				selectedQuery: {},
				infoDialogOpen: false,
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
			selectedDevices: function (newDevices) {
				if (newDevices.length === 1) {
					this.selectedTags = this.device.deviceList.data.filter(function (device) {
						return device.id === newDevices[0]
					})[0].tags
				} else {
					if (!this.selectedTags.length) { return }
					this.device.deviceList.data.forEach((device) => {
						if (newDevices.indexOf(device.id) > -1) {
							this.selectedTags = this.selectedTags.filter(function (tag) {
								if (!device.tags.length) { return }
								return device.tags.indexOf(tag) > -1
							})
						}
					})
				}
			}
		},
		created () {
            if (!this.device.fields.unique || !this.device.fields.unique.length) {
				this.fetchFields()
			}
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
				saveDeviceTags: SAVE_DEVICE_TAGS
			}),
			extractQuery () {
				this.selectedQuery = strToQuery(this.queryDropdown.value)
			},
			extractValue () {
				this.queryDropdown.value = queryToStr(this.selectedQuery)
			},
            executeQuery() {
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
					query: this.selectedQuery,
					name: this.saveQueryModal.name,
					callback: () => this.saveQueryModal.open = false
				})
			},
			saveTags () {
				if (!this.selectedDevices || !this.selectedDevices.length || !this.selectedTags
                    || !this.selectedTags.length) {
					return
				}
				this.saveDeviceTags({devices: this.selectedDevices, tags: this.selectedTags})
			},
			executeQuickView (deviceId) {
				this.fetchDevice(deviceId)
                this.$el.querySelector(`.table-row[data-id='${deviceId}']`).classList.add('active')
				this.infoDialogOpen = true
			},
			closeQuickView () {
				if (this.infoDialogOpen) {
					this.$el.querySelector('.table-row.active').classList.remove('active')
				}
				this.infoDialogOpen = false
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
                    &:after {
                        margin-top: 16px;
                    }
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
                    stroke: $color-text;
                    stroke-width: 20px;
                }
            }
        }
    }

</style>