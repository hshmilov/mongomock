<template>
    <div class="x-data-entity">
        <template v-if="fields.generic && entity.generic">
            <tabs>
                <tab title="Basic Info" id="basic" key="basic" :selected="true">
                    <x-schema-list :data="entity.generic.basic" :schema="{type: 'array', items: fields.generic}"/>
                </tab>
                <tab v-for="item, i in entityGenericAdvanced" :title="item.title" :id="i" :key="i">
                    <x-schema-list :data="item.data" :schema="item.schema" />
                </tab>
                <tab v-for="item, i in entity.generic.data" :title="item.name" :id="`data_${i}`" :key="`data_${i}`">
                    <x-custom-data :data="item.data"/>
                </tab>
                <tab title="Tags" id="tags" key="tags">
                    <div @click="activateTag" class="link tag-edit">Edit Tags</div>
                    <div class="x-grid x-grid-col-2 w-20">
                        <template v-for="label in entity.labels">
                            <div>{{ label }}</div>
                            <div class="link" @click="removeTag(label)">Remove</div>
                        </template>
                    </div>
                </tab>
            </tabs>
        </template>
        <template v-if="fields.specific">
            <tabs>
                <tab v-for="item, i in sortedSpecificData" :id="item.data.id+item.plugin_unique_name"
                     :key="item.data.id+item.plugin_unique_name" :selected="!i" :title="item.pretty_name"
                     :logo="item.plugin_name" :outdated="item.outdated">
                    <div class="d-flex tab-header">
                        <div class="flex-expand">Data From: {{ item.client_used }}</div>
                        <div v-if="viewBasic" @click="viewBasic=false" class="link">View advanced</div>
                        <div v-if="!viewBasic" @click="viewBasic=true" class="link">View basic</div>
                    </div>
                    <x-schema-list v-if="viewBasic && fields.specific[item.plugin_name]"
                                   :data="item.data" :schema="fields.schema.specific[item.plugin_name]"/>
                    <div v-if="!viewBasic">
                        <tree-view :data="item.data.raw" :options="{rootObjectKey: 'raw', maxDepth: 1}"/>
                    </div>
                </tab>
            </tabs>
        </template>
        <x-tag-modal :module="module" :entities="entities" :tags="entity.labels" ref="tagModal" />
    </div>
</template>

<script>
	import Tabs from '../../components/tabs/Tabs.vue'
	import Tab from '../../components/tabs/Tab.vue'
	import xSchemaList from '../../components/schema/SchemaList.vue'
	import xCustomData from '../../components/schema/CustomData.vue'
	import xTagModal from '../../components/popover/TagModal.vue'

    import { mapState, mapActions } from 'vuex'
    import { FETCH_DATA_FIELDS, FETCH_DATA_BY_ID } from '../../store/actions'
	import { pluginMeta } from '../../static.js'

	export default {
		name: 'x-data-entity',
        components: {Tabs, Tab, xSchemaList, xCustomData, xTagModal},
        props: { module: {required: true}},
		data () {
			return {
				viewBasic: true,
				entities: [this.$route.params.id]
			}
		},
        computed: {
            ...mapState({
                entity(state) {
                	return state[this.module].current.data
                },
                fields(state) {
                	return state[this.module].fields.data
                }
            }),
            entityId() {
				return this.$route.params.id
            },
			entityGenericAdvanced() {
				if (!this.entity.generic || !this.entity.generic.advanced) return []
				return this.entity.generic.advanced.filter(item => item.data && item.data.length).map((item) => {
					let schema = this.getAdvancedFieldSchema(item.name)
					return { ...item,
						title: schema.title,
						schema: { ...schema, title: undefined }
					}
				})
			},
			sortedSpecificData () {
				if (!this.entity.specific) return []
				let lastSeen = new Set()
				return [ ...this.entity.specific].sort((first, second) => {
					// Adapters with no last_seen field go first
					if (!second.data.last_seen) return 1
					if (!first.data.last_seen) return -1
					// Turn strings into dates and subtract them to get a negative, positive, or zero value.
					return new Date(second.data.last_seen) - new Date(first.data.last_seen)
				}).map((item) => {
                    item.pretty_name = item.plugin_name
                    if (pluginMeta[item.plugin_name] && pluginMeta[item.plugin_name].title) {
						item.pretty_name = pluginMeta[item.plugin_name].title
                    }
					if (lastSeen.has(item.plugin_name)) return { ...item, outdated: true }
					lastSeen.add(item.plugin_name)
					return item
				})
			}
        },
        methods: {
            ...mapActions({
                fetchDataFields: FETCH_DATA_FIELDS, fetchDataByID: FETCH_DATA_BY_ID
            }),
			getAdvancedFieldSchema(field) {
				if (!this.fields.schema || !this.fields.schema.generic) return {}
				return this.fields.schema.generic.items.filter(schema => schema.name === field)[0]
			},
			removeTag (label) {
				if (!this.$refs || !this.$refs.tagModal) return
				this.$refs.tagModal.removeEntitiesLabels([label])
			},
			activateTag() {
				if (!this.$refs || !this.$refs.tagModal) return
				this.$refs.tagModal.activate()
			}
        },
		created () {
			if (!this.fields || !this.fields.generic) {
				this.fetchDataFields({ module: this.module })
			}
			if (!this.entity || this.entity.internal_axon_id !== this.entityId) {
				this.fetchDataByID({ module: this.module, id: this.entityId })
			}
		}
	}
</script>

<style lang="scss">
    .x-data-entity {
        height: 100%;
        .tabs {
            width: 100%;
            height: 48%;
            margin-bottom: 12px;
            padding-bottom: 24px;
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
                height: calc(100% - 60px);
                .object {
                    width: calc(100% - 24px);
                }
            }
            .tag-edit {
                text-align: right;
            }
        }
    }
</style>