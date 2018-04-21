<template>
    <x-page :breadcrumbs="[
    	{ title: 'devices', path: { name: 'Devices'}},
    	{ title: deviceName }
    ]">
        <template v-if="deviceFields.generic && deviceData.generic">
            <tabs>
                <tab title="Basic Info" id="basic" key="basic" :selected="true">
                    <x-schema-list :data="deviceData.generic.basic" :schema="{type: 'array', items: deviceFields.generic}"/>
                </tab>
                <tab v-for="item, i in deviceDataGenericAdvanced" :title="item.title" :id="i" :key="i">
                    <x-schema-list :data="item.data" :schema="item.schema" />
                </tab>
                <tab v-for="item, i in deviceData.generic.data" :title="item.name" :id="`data_${i}`" :key="`data_${i}`">
                    <x-custom-data :data="item.data"/>
                </tab>
                <tab title="Tags" id="tags" key="tags">
                    <div @click="tag.isActive = true" class="link tag-edit">Edit Tags</div>
                    <div v-for="label in deviceData.labels" class="col-4 d-flex tag-content">
                        <div>{{ label }}</div>
                        <div class="link" @click="removeTag(label)">Remove</div>
                    </div>
                </tab>
            </tabs>
        </template>
        <template v-if="deviceFields.specific">
            <tabs>
                <tab v-for="item, i in sortedSpecificData" :id="item.data.id+item.plugin_unique_name"
                     :key="item.data.id+item.plugin_unique_name" :selected="!i" :title="getAdapterName(item.plugin_name)"
                     :logo="item.plugin_name" :outdated="item.outdated">
                    <div class="d-flex tab-header">
                        <div class="flex-expand">Data From: {{ item.client_used }}</div>
                        <div v-if="viewBasic" @click="viewBasic=false" class="link">View advanced</div>
                        <div v-if="!viewBasic" @click="viewBasic=true" class="link">View basic</div>
                    </div>
                    <x-schema-list v-if="viewBasic && deviceFields.specific[item.plugin_name]"
                                   :data="item.data" :schema="deviceFields.schema.specific[item.plugin_name]"/>
                    <div v-if="!viewBasic">
                        <tree-view :data="item.data.raw" :options="{rootObjectKey: 'raw', maxDepth: 1}"/>
                    </div>
                </tab>
            </tabs>
        </template>
        <feedback-modal v-model="tag.isActive" :handleSave="saveTags" :message="`Tagged ${devices.length} devices!`">
            <searchable-checklist title="Tag as:" :items="device.labelList.data" :searchable="true"
                                  :extendable="true" v-model="tag.selected"/>
        </feedback-modal>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import NamedSection from '../../components/NamedSection.vue'
	import Tabs from '../../components/tabs/Tabs.vue'
	import Tab from '../../components/tabs/Tab.vue'
	import xSchemaList from '../../components/schema/SchemaList.vue'
	import xCustomData from '../../components/schema/CustomData.vue'
	import FeedbackModal from '../../components/popover/FeedbackModal.vue'
	import SearchableChecklist from '../../components/SearchableChecklist.vue'
	import TagsMixin from '../../mixins/tags'

	import { mapState, mapMutations, mapActions } from 'vuex'
	import {
		FETCH_DEVICE, UPDATE_DEVICE,
		CREATE_DEVICE_LABELS, DELETE_DEVICE_LABELS, FETCH_LABELS,
	} from '../../store/modules/device.js'
	import { pluginMeta } from '../../static.js'
    import { FETCH_DATA_FIELDS } from '../../store/actions'

	export default {
		name: 'device-config-container',
		components: {
			xPage, NamedSection, Tabs, Tab, xSchemaList, xCustomData,
			FeedbackModal, SearchableChecklist
		},
		mixins: [TagsMixin],
		computed: {
			...mapState(['device']),
			deviceId () {
				return this.$route.params.id
			},
			deviceData () {
				return this.device.deviceDetails.data
			},
			deviceName () {
				if (!this.deviceData || !this.deviceData.generic) {
					return ''
				}
                let name = this.deviceData.generic.basic['specific_data.data.hostname']
                    || this.deviceData.generic.basic['specific_data.data.name']
                    || this.deviceData.generic.basic['specific_data.data.pretty_id']
                if (Array.isArray(name) && name.length) {
					return name[0]
                } else if (!Array.isArray(name)) {
					return name
                }
			},
			deviceFields () {
				return this.device.data.fields.data
			},
            deviceDataGenericAdvanced() {
				if (!this.deviceData.generic || !this.deviceData.generic.advanced) return []
				return this.deviceData.generic.advanced.filter(item => item.data && item.data.length).map((item) => {
					let schema = this.getAdvancedFieldSchema(item.name)
					return { ...item,
						title: schema.title,
                        schema: { ...schema, title: undefined }
                    }
                })
            },
			sortedSpecificData () {
				if (!this.deviceData.specific) return []
				let lastSeen = new Set()
				return [ ...this.deviceData.specific].sort((first, second) => {
					// Adapters with no last_seen field go first
					if (!second.data.last_seen) return 1
					if (!first.data.last_seen) return -1
					// Turn strings into dates and subtract them to get a negative, positive, or zero value.
					return new Date(second.data.last_seen) - new Date(first.data.last_seen)
				}).map((item) => {
					if (lastSeen.has(item.plugin_name)) return { ...item, outdated: true }
					lastSeen.add(item.plugin_name)
					return item
				})
			},
			currentTags () {
				return this.deviceData.labels
			}
		},
		data () {
			return {
				viewBasic: true,
				devices: [this.$route.params.id]
			}
		},
		methods: {
			...mapMutations({updateDevice: UPDATE_DEVICE}),
			...mapActions({
				fetchDevice: FETCH_DEVICE, fetchDataFields: FETCH_DATA_FIELDS,
				deleteDeviceTags: DELETE_DEVICE_LABELS, createDeviceTags: CREATE_DEVICE_LABELS,
				fetchLabels: FETCH_LABELS
			}),
			getAdapterName (pluginName) {
				if (!pluginMeta[pluginName]) {
					return pluginName
				}
				return pluginMeta[pluginName].title || pluginName
			},
            getAdvancedFieldSchema(field) {
				if (!this.deviceFields.schema || !this.deviceFields.schema.generic) return {}
				return this.deviceFields.schema.generic.items.filter(schema => schema.name === field)[0]
            },
			removeTag (label) {
				this.deleteDeviceTags({devices: [this.deviceId], labels: [label]})
			}
		},
		created () {
			if (!this.deviceFields || !this.deviceFields.generic) {
				this.fetchDataFields({module: 'device'})
			}
			if (!this.deviceData || this.deviceData.internal_axon_id !== this.deviceId) {
				this.fetchDevice(this.deviceId)
			}
			if (!this.device.labelList.data || !this.device.labelList.data.length) {
				this.fetchLabels()
			}
		}
	}
</script>

<style lang="scss">

    .tabs {
        width: 100%;
        height: 48%;
        margin-bottom: 12px;
        .tab-header {
            border-bottom: 1px solid #ddd;
            margin-bottom: 12px;
            padding-bottom: 8px;
            margin-left: -12px;
            margin-right: -12px;
            padding-left: 12px;
            padding-right: 12px;
        }
        .tab-content {
            overflow: auto;
            height: calc(100% - 40px);
        }
        .tag-edit {
            text-align: right;
        }
    }
</style>