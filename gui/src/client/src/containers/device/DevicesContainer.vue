<template>
    <scrollable-page title="devices" class="device">
        <card title="query">
            <span slot="cardActions">
                <action-bar :actions="[
                  { name: advancedView? 'Basic' : 'Advanced', perform: performToggleAdvanced },
                  { name: 'Add to Dashboard', perform: performAddToDashboard },
                  { name: 'Watch Query', perform: performWatchQuery },
                  { name: 'Save Query', perform: performSaveQuery }
                ]"></action-bar>
            </span>
            <generic-form slot="cardContent" :schema="queryFields" :values="queryData" :submitHandler="performQuery"
                          submitLabel="Go!" :horizontal="true" :advancedView="advancedView"></generic-form>
        </card>
        <card :title="`devices (${device.retrievedDevices.data.length})`">
            <span slot="cardActions" class="device-table-actions">
                <dropdown-menu :positionRight="true">
                    <i slot="dropdownTrigger" class="icon-tag"></i>
                    <searchable-checklist slot="dropdownContent" title="Tag as:" :items="device.tags"
                                          :actionOne="toggleDeviceTag">
                        <template slot="checklistActions">
                            <a @click="saveDeviceTags({ devices: selectedDevices, tags: selectedTags })">Save</a>
                        </template>
                    </searchable-checklist>
                </dropdown-menu>
                <dropdown-menu :positionRight="true">
                    <i slot="dropdownTrigger" class="icon-eye"></i>
                    <searchable-checklist slot="dropdownContent" title="Show fields:" :items="device.fields"
                                          :actionOne="toggleDeviceField"></searchable-checklist>
                </dropdown-menu>
            </span>
            <paginated-table slot="cardContent" :fetching="device.retrievedDevices.fetching"
                             :data="device.retrievedDevices.data" :error="device.retrievedDevices.error"
                             :fields="selectedFields" :fetchData="fetchDevices"
                             :toggleOne="toggleDevice" :toggleAll="toggleDeviceAll"></paginated-table>
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

    import { mapState, mapMutations, mapGetters, mapActions } from 'vuex'
    import {
        FETCH_DEVICES, TOGGLE_DEVICE, TOGGLE_DEVICE_ALL,
        TOGGLE_DEVICE_FIELD, TOGGLE_DEVICE_TAG, SAVE_DEVICE_TAGS
    } from '../../store/modules/device'
    import { SAVE_QUERY } from '../../store/modules/query'

    export default {
        name: 'devices-container',
        components: {
            ScrollablePage, Card,
            ActionBar, GenericForm,
            DropdownMenu, SearchableChecklist,
            PaginatedTable },
        computed: {
            ...mapState(['device']),
            ...mapGetters(['selectedFields', 'queryFields', 'deviceNames', 'selectedDevices', 'selectedTags'])
        },
        data () {
            return {
                queryData: {},
                advancedView: false
            }
        },
        methods: {
            ...mapActions({
                fetchDevices: FETCH_DEVICES,
                saveQuery: SAVE_QUERY,
                saveDeviceTags: SAVE_DEVICE_TAGS
            }),
            ...mapMutations({
                toggleDevice: TOGGLE_DEVICE,
                toggleDeviceAll: TOGGLE_DEVICE_ALL,
                toggleDeviceField: TOGGLE_DEVICE_FIELD,
                toggleDeviceTag: TOGGLE_DEVICE_TAG
            }),
            performAddToDashboard() {
                console.log("Adding to dashboard")
            },
            performWatchQuery() {
                console.log("Watching query")
            },
            performSaveQuery() {
                console.log("Save query")
            },
            performToggleAdvanced() {
                this.advancedView = !this.advancedView
            },
            performQuery(event) {
                event.preventDefault()
                event.stopPropagation()
                this.saveQuery({
                    query: this.queryData
                })
            }
        }
    }
</script>


<style lang="scss">
    .device {
        .device-table-actions {
            flex: 0 1 auto;
            display: flex;
            flex-flow: row;
            .dropdown {
                margin-left: 8px;
                .checkbox {
                    margin-top: 8px;
                    width: 180px;
                    &:first-of-type {
                        margin-top: 0;
                    }
                }
            }
        }
    }
</style>