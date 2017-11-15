<template>
    <scrollable-page title="devices">
        <card title="query">
            <span slot="cardActions">
                <action-bar :actions="[
                  { name: 'Save Query', perform: executeSaveQuery }
                ]"></action-bar>
            </span>
            <generic-form slot="cardContent" :schema="queryFields" :values="query.currentQuery"
                          submitLabel="Go!" :submitHandler="updateQuery" :horizontal="true"></generic-form>
        </card>
        <card :title="`devices (${device.deviceList.data.length})`">
            <div slot="cardActions" class="card-actions">
                <dropdown-menu :positionRight="true" animateClass="scale-up right">
                    <i slot="dropdownTrigger" class="icon-tag"></i>
                    <searchable-checklist slot="dropdownContent" slot-scope="props" title="Tag as:"
                                          :items="device.tagList.data" :hasSearch="true" :producesNew="true"
                                          v-model="selectedTags" v-on:save="saveTags()" :explicitSave="true"
                                          :onDone="props.onDone"></searchable-checklist>
                </dropdown-menu>
                <dropdown-menu :positionRight="true" animateClass="scale-up right" menuClass="w-md">
                    <img slot="dropdownTrigger" src="/src/assets/images/general/filter.png">
                    <searchable-checklist slot="dropdownContent" title="Show fields:" :items="device.fields"
                                          :hasSearch="true" v-model="selectedFields"></searchable-checklist>
                </dropdown-menu>
            </div>
            <div slot="cardContent" v-on-clickaway="closeQuickView">
                <paginated-table :fetching="device.deviceList.fetching" :data="device.deviceList.data"
                                 :error="device.deviceList.error" :fields="fields" :fetchData="fetchDevices"
                                 v-model="selectedDevices" :filter="query.currentQuery"
                                 :actions="[{ handler: executeQuickView, trigger: 'icon-eye'}]"></paginated-table>
                <info-dialog :open="infoDialogOpen" title="Device Quick View" :closeDialog="closeQuickView.bind(this)">
                    <div class="d-flex flex-row justify-content-between p-3">
                        <div>{{ device.deviceDetails.name }}</div>
                        <div>{{ device.deviceDetails.IP }}</div>
                    </div>
                    <div v-if="device.deviceDetails.data.adapters" class="d-flex flex-column justify-content-between p-3">
                        <div>Adapters</div>
                        <hr class="title-separator">
                        <image-list :data="device.deviceDetails.data.adapters" :vertical="true"
                                    :names="device.adapterNames"></image-list>
                    </div>
                    <div v-if="device.deviceDetails.data.tags && device.deviceDetails.data.tags.length" class="d-flex flex-column justify-content-between align-items-start p-3">
                        <div>Tags</div>
                        <hr class="title-separator">
                        <div><div v-for="tag in device.deviceDetails.data.tags" class="tag-list-item">{{ tag }}</div>
                        </div>
                    </div>
                </info-dialog>
            </div>
        </card>
    </scrollable-page>
</template>


<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
    import ActionBar from '../../components/ActionBar.vue'
    import GenericForm from '../../components/GenericForm.vue'
    import DropdownMenu from '../../components/DropdownMenu.vue'
    import SearchableChecklist from '../../components/SearchableChecklist.vue'
    import PaginatedTable from '../../components/PaginatedTable.vue'
    import InfoDialog from '../../components/InfoDialog.vue'
    import ImageList from '../../components/ImageList.vue'
    import { mixin as clickaway } from 'vue-clickaway'

    import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { FETCH_FIELDS,  FETCH_DEVICES, FETCH_DEVICE, FETCH_TAGS, SAVE_DEVICE_TAGS } from '../../store/modules/device'
    import { UPDATE_QUERY, SAVE_QUERY } from '../../store/modules/query'

    export default {
        name: 'devices-container',
        components: {
            ImageList,
            ScrollablePage, Card,
            ActionBar, GenericForm,
            DropdownMenu, SearchableChecklist,
            PaginatedTable, InfoDialog },
        mixins: [ clickaway ],
        computed: {
            ...mapState(['device', 'query']),
            ...mapGetters(['deviceNames']),
            fields() {
                let _this = this
                return this.device.fields.filter(function(field) {
                    return _this.selectedFields.indexOf(field.path) > -1
                })
            },
            queryFields() {
				return this.fields.filter((field) => {
					return field.querySchema !== undefined && (this.selectedFields.indexOf(field.path) > -1)
				}).map(function (field) {
					return {
						path: field.path, name: field.name,
						...field.querySchema
					}
				})
            }
        },
        data () {
            return {
                selectedTags: [],
                selectedFields: [],
                selectedDevices: [],
                infoDialogOpen: false
            }
        },
        watch: {
        	selectedDevices: function(newDevices) {
        		if (newDevices.length === 1) {
        			this.selectedTags = this.device.deviceList.data.filter(function(device) {
        				return device.id === newDevices[0]
                    })[0].tags
                } else {
        			if (!this.selectedTags.length) { return }
        			this.device.deviceList.data.forEach((device) => {
        				if (newDevices.indexOf(device.id) > -1) {
        					this.selectedTags = this.selectedTags.filter(function(tag) {
        						if (!device.tags.length) { return }
        						return device.tags.indexOf(tag) > -1
                            })
                        }
                    })
                }
            }
        },
        created() {
        	this.fetchFields()
        	this.fetchTags()
            this.selectedFields = this.device.fields.filter(function(field) {
                return field.selected
            }).map(function(field) {
                return field.path
            })
        },
        methods: {
            ...mapMutations({
                updateQuery: UPDATE_QUERY
            }),
            ...mapActions({
                fetchFields: FETCH_FIELDS,
                fetchDevices: FETCH_DEVICES,
				fetchDevice: FETCH_DEVICE,
				saveQuery: SAVE_QUERY,
				fetchTags: FETCH_TAGS,
				saveDeviceTags: SAVE_DEVICE_TAGS
            }),
            executeSaveQuery() {
                this.saveQuery({ query: this.query.currentQuery, name: 'shira'})
            },
            saveTags() {
                this.saveDeviceTags({ devices: this.selectedDevices, tags: this.selectedTags })
            },
            executeQuickView(event, deviceId) {
            	this.fetchDevice(deviceId)
                event.target.parentElement.parentElement.parentElement.classList.add('active')
                this.infoDialogOpen = true
            },
            closeQuickView() {
            	if (this.infoDialogOpen) {
                    this.$el.querySelector(".table-row.active").classList.remove("active")
                }
                this.infoDialogOpen = false
            }
        }
    }
</script>


<style lang="scss">

</style>