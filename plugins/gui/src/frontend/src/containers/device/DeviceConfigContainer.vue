<template>
    <scrollable-page :breadcrumbs="[
    	{ title: 'devices', path: { name: 'Devices'}},
    	{ title: deviceName }
    ]">
        <div class="row">
            <div class="col-4">
                <named-section title="Device Generic Fields" iconName="action/add_field">
                    <card>
                        <array :items="deviceFields.items" v-if="deviceData.data"
                               :data="deviceData.data" :required="deviceFields.required"></array>
                    </card>
                </named-section>
                <named-section v-if="deviceData.tags && deviceData.tags.length" title="Tags" fontClass="icon-tag">
                    <card>
                        <div v-for="tag in deviceData.tags" class="d-flex tag-content">
                            <div>{{tag.tagname}}</div>
                            <div class="link" @click="removeTag(tag.tagname)">Remove</div>
                        </div>
                    </card>
                </named-section>
            </div>
            <div class="col-8">
                <named-section title="Adapter Specific Fields" iconName="action/add_field">
                    <tabs>
                        <tab v-for="device, index in deviceData.adapters" :title="getAdapterName(device.plugin_name)"
                             :id="device.plugin_name" :selected="index === 0">
                            <div class="d-flex tab-header">
                                <div>Data From: {{ device.client_used }}</div>
                                <div v-if="viewDataBasic" @click="viewDataBasic=false" class="link">View advanced</div>
                                <div v-if="!viewDataBasic" @click="viewDataBasic=true" class="link">View basic</div>
                            </div>
                            <array v-if="viewDataBasic" :items="deviceFields.items" :data="device.data"></array>
                            <div v-if="!viewDataBasic">
                                <tree-view :data="device.data.raw" :options="{rootObjectKey: 'raw', maxDepth: 1}"></tree-view>
                            </div>
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
    import Array from '../../components/data/Array.vue'
    import { FETCH_DEVICE, DELETE_DEVICE_TAGS } from '../../store/modules/device.js'
    import { adapterStaticData } from '../../store/modules/adapter.js'
    import { mapState, mapActions } from 'vuex'

	export default {
		name: 'device-config-container',
        components: {ScrollablePage, NamedSection, Card, Tabs, Tab},
        computed: {
            ...mapState(['device']),
            deviceId() {
            	return this.$route.params.id
            },
            deviceData() {
            	return this.device.deviceDetails.data
            },
            deviceName() {
            	if (!this.deviceData.data) {
            		return ''
                }
            	return this.deviceData.data.hostname
            },
            deviceFields() {
            	return this.device.deviceFields.data
            }
        },
        data() {
			return {
				viewDataBasic: true
            }
        },
        methods: {
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