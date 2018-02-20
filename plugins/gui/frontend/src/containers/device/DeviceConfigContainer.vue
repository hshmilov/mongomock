<template>
    <scrollable-page :breadcrumbs="[
    	{ title: 'devices', path: { name: 'Devices'}},
    	{ title: deviceName }
    ]">
        <div class="row" v-if="deviceFields.generic">
            <!--<named-section title="General Data" icon-name="action/add_field">-->
                <tabs v-if="deviceData.generic_data && deviceData.generic_data.length">
                    <tab title="Basic Info" id="basic" key="basic" :selected="true">
                        <x-schema-list :data="deviceDataGenericBasic" :schema="deviceFields.generic"></x-schema-list>
                    </tab>
                    <tab v-for="item, i in deviceDataGenericAdvanced" :title="item.name" :id="i" :key="i">
                        <x-custom-data :data="item.data"></x-custom-data>
                    </tab>
                    <tab title="Tags" id="tags" key="tags" v-if="deviceData.labels && deviceData.labels.length">
                        <div v-for="label in deviceData.labels" class="col-4 d-flex tag-content">
                            <div>{{ label }}</div>
                            <div class="link" @click="removeTag(label)">Remove</div>
                        </div>
                    </tab>
                </tabs>
            <!--</named-section>-->
        </div>
        <div class="row" v-if="deviceFields.specific">
            <!--<named-section title="Adapter Specific Data" icon-name="action/add_field">-->
                <tabs>
                    <tab v-for="item, i in sortedSpecificData" :id="item.data.id+item.plugin_unique_name"
                         :key="item.data.id+item.plugin_unique_name"
                         :selected="!i" :title="getAdapterName(item.plugin_name)"
                         :logo="item.plugin_name" :outdated="item.outdated">
                        <div class="d-flex tab-header">
                            <div>Data From: {{ item.client_used }}</div>
                            <div v-if="viewBasic" @click="viewBasic=false" class="link">View advanced</div>
                            <div v-if="!viewBasic" @click="viewBasic=true" class="link">View basic</div>
                        </div>
                        <x-schema-list v-if="viewBasic && deviceFields.specific[item.plugin_name]" :data="item.data"
                                       :schema="deviceFields.specific[item.plugin_name]"></x-schema-list>
                        <div v-if="!viewBasic">
                            <tree-view :data="item.data.raw" :options="{rootObjectKey: 'raw', maxDepth: 1}"></tree-view>
                        </div>
                    </tab>
                </tabs>
            <!--</named-section>-->
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
	import {
		FETCH_DEVICE,
		CREATE_DEVICE_LABELS,
		DELETE_DEVICE_LABELS,
		UPDATE_DEVICE,
		FETCH_DEVICE_FIELDS
	} from '../../store/modules/device.js'
	import { adapterStaticData } from '../../store/modules/adapter.js'
	import { mapState, mapMutations, mapActions } from 'vuex'

	export default {
		name: 'device-config-container',
		components: {ScrollablePage, NamedSection, Card, Tabs, Tab, xSchemaList, xCustomData},
		computed: {
			...mapState(['device']),
			deviceId () {
				return this.$route.params.id
			},
			deviceData () {
				return this.device.deviceDetails.data
			},
			sortedSpecificData () {
				if (!this.deviceData || !this.deviceData.specific_data) return []
				this.deviceData.specific_data.sort((first, second) => {
					// Adapters with no last_seen field go first
					if (!second.data.last_seen) return 1
					if (!first.data.last_seen) return -1

					// Turn strings into dates and subtract them to get a negative, positive, or zero value.
					return new Date(second.data.last_seen) - new Date(first.data.last_seen)
				})
				let lastSeen = new Set()
				this.deviceData.specific_data.forEach((item) => {
					if (lastSeen.has(item.plugin_name)) {
						item.outdated = true
						return
					}
					lastSeen.add(item.plugin_name)
				})
				return this.deviceData.specific_data
			},
			deviceName () {
				if (!this.deviceData.generic_data || !this.deviceData.generic_data.length) {
					return ''
				}
				return this.deviceData.generic_data[0].hostname || this.deviceData.generic_data[0].name
					|| this.deviceData.generic_data[0].pretty_id
			},
			deviceFields () {
				return this.device.deviceFields.data
			},
            deviceFieldsGenericAdvanced() {
				return ['installed_software', 'security_patches', 'users']
            },
            deviceDataGenericBasic() {
				if (!this.deviceData.generic_data || !this.deviceData.generic_data.length) return {}

				let genericBasic = { ...this.deviceData.generic_data[0] }
                this.deviceFieldsGenericAdvanced.forEach((field) => {
					delete genericBasic[field]
                })
                return genericBasic
            },
			deviceDataGenericAdvanced() {
				if (!this.deviceData.generic_data || !this.deviceData.generic_data.length) return {}

				return Object.keys(this.deviceData.generic_data[0]).filter((name) => {
					return this.deviceFieldsGenericAdvanced.includes(name)
                }).map((name) => {
					return { name: name.split('_').join(' '), data: this.deviceData.generic_data[0][name] }
                }).concat(this.deviceData.generic_data.slice(1))
			}
		},
		data () {
			return {
				viewBasic: true,
                tag: {
					isActive: false,
                    value: ''
                }
			}
		},
		methods: {
			...mapMutations({updateDevice: UPDATE_DEVICE}),
			...mapActions({
				fetchDevice: FETCH_DEVICE, deleteDeviceTags: DELETE_DEVICE_LABELS,
                createDeviceTags: CREATE_DEVICE_LABELS,
				fetchDeviceFields: FETCH_DEVICE_FIELDS
			}),
			getAdapterName (pluginName) {
				if (!adapterStaticData[pluginName]) {
					return pluginName
				}
				return adapterStaticData[pluginName].name
			},
			removeTag (label) {
				this.deleteDeviceTags({devices: [this.deviceId], labels: [label]})
			}
		},
		created () {
			if (!this.deviceFields || !this.deviceFields.generic) {
				this.fetchDeviceFields()
			}
			if (!this.deviceData || this.deviceData.internal_axon_id !== this.deviceId) {
				this.fetchDevice(this.deviceId)
			}
		}
	}
</script>

<style lang="scss">

    .tabs {
        width: 100%;
        margin-bottom: 12px;
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
            .tag-content {
                .link {
                    flex: 1 0 auto;
                    text-align: right;
                }
            }
        }
    }
</style>