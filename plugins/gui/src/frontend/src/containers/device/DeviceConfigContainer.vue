<template>
    <scrollable-page :breadcrumbs="[
    	{ title: 'devices', path: { name: 'Devices'}},
    	{ title: deviceName }
    ]">
        <div class="row">
            <div class="col-4">
                <named-section title="Device Generic Fields" icon-name="action/add_field" v-if="deviceData.data">
                    <card>
                        <x-schema-list :data="deviceData.data" :schema="deviceFields" :limit="true"></x-schema-list>
                    </card>
                </named-section>
                <named-section v-if="deviceData.tags && deviceData.tags.length" title="Tags" font-class="icon-tag">
                    <card>
                        <div v-for="tag in deviceData.tags" class="d-flex tag-content">
                            <div>{{tag.tagname}}</div>
                            <div class="link" @click="removeTag(tag.tagname)">Remove</div>
                        </div>
                    </card>
                </named-section>
            </div>
            <div class="col-8">
                <named-section title="Adapter Specific Fields" icon-name="action/add_field">
                    <tabs>
                        <tab v-for="adapter, i in sortedAdapters" :id="adapter.data.id" :key="adapter.data.id"
                             :selected="!i" :title="getAdapterName(adapter.plugin_name)"
                             :logo="adapter.plugin_name" :outdated="adapter.outdated">
                            <div class="d-flex tab-header">
                                <div>Data From: {{ adapter.client_used }}</div>
                                <div v-if="viewBasic" @click="viewBasic=false" class="link">View advanced</div>
                                <div v-if="!viewBasic" @click="viewBasic=true" class="link">View basic</div>
                            </div>
                            <x-schema-list v-if="viewBasic" :schema="deviceFields" :data="adapter.data"></x-schema-list>
                            <div v-if="!viewBasic">
                                <tree-view :data="device.data.raw" :options="{rootObjectKey: 'raw', maxDepth: 1}"></tree-view>
                            </div>
                        </tab>
                    </tabs>
                </named-section>
                <named-section title="Plugin Data" icon-name="action/add_field" v-if="hasFieldTags">
                    <tabs>
                        <tab v-for="tag, i in deviceData.dataTags" :title="tag.tagname" :id="i" :key="i" :selected="!i">
                            <x-custom-data :data="tag.tagvalue"></x-custom-data>
                        </tab>
                    </tabs>
                </named-section>
            </div>
        </div>
    </scrollable-page>
</template>

<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import NamedSection from '../../components/NamedSection.vue'
    import Card from '../../components/Card.vue'
    import Tabs from '../../components/tabs/Tabs.vue'
    import Tab from '../../components/tabs/Tab.vue'
    import xSchemaList from '../../components/data/SchemaList.vue'
    import xCustomData from '../../components/data/CustomData.vue'
    import { FETCH_DEVICE, DELETE_DEVICE_TAGS, UPDATE_DEVICE } from '../../store/modules/device.js'
    import { adapterStaticData } from '../../store/modules/adapter.js'
    import { mapState, mapMutations, mapActions } from 'vuex'

	export default {
		name: 'device-config-container',
        components: {ScrollablePage, NamedSection, Card, Tabs, Tab, xSchemaList, xCustomData},
        computed: {
            ...mapState(['device']),
            deviceId() {
            	return this.$route.params.id
            },
            deviceData() {
            	return this.device.deviceDetails.data
            },
            sortedAdapters() {
                if (!this.deviceData || !this.deviceData.adapters) return []
                this.deviceData.adapters.sort((first, second) => {
                	// Adapters with no last_seen field go first
                    if(!second.data.last_seen) return 1
                    if(!first.data.last_seen) return -1

                    // Turn strings into dates and subtract them to get a negative, positive, or zero value.
                    return new Date(second.data.last_seen) - new Date(first.data.last_seen)
                })
                let lastSeen = new Set()
                this.deviceData.adapters.forEach((adapter) => {
                    if (lastSeen.has(adapter.plugin_name)) {
                    	adapter.outdated = true
                        return
					}
                    lastSeen.add(adapter.plugin_name)
                })
                return this.deviceData.adapters
            },
            deviceName() {
            	if (!this.deviceData.data) {
            		return ''
                }
            	return this.deviceData.data.hostname || this.deviceData.data.name || this.deviceData.data.pretty_id
            },
            deviceFields() {
            	return this.device.deviceFields.data
            },
            hasFieldTags() {
            	return this.deviceData.dataTags && Object.keys(this.deviceData.dataTags).length
            }
        },
        data() {
			return {
				viewBasic: true
            }
        },
        methods: {
            ...mapMutations({ updateDevice: UPDATE_DEVICE }),
            ...mapActions({ fetchDevice: FETCH_DEVICE, deleteDeviceTags: DELETE_DEVICE_TAGS }),
            getAdapterName(pluginName) {
            	if (!adapterStaticData[pluginName]) {
            		return pluginName
                }
            	return adapterStaticData[pluginName].name
            },
            removeTag(tag) {
            	this.deleteDeviceTags({devices: [this.deviceId], tags: [tag]})
            }
        },
        created() {
			if (!this.deviceData || this.deviceData.internal_axon_id !== this.deviceId) {
				this.updateDevice({ fetching: false, error: '', data: {
					internal_axon_id: this.deviceId, adapters: [], tags: [], data: {}
                }})
				this.fetchDevice(this.deviceId)
			}
        }
	}
</script>

<style lang="scss">

    .section {
        .card-body {
            font-size: 14px;
            .tag-content {
                .link {
                    flex: 1 0 auto;
                    text-align: right;
                }
            }
        }
    }
    .tab-pane {
        font-size: 14px;
        .tab-header {
            border-bottom: 1px solid #ddd;
            margin-bottom: 12px;
            padding-bottom: 8px;
            margin-left: -12px;
            margin-right: -12px;
            padding-left: 12px;
            padding-right: 12px;
            .link {
                flex: 1 0 auto;
                text-align: right;
            }
        }
    }
</style>