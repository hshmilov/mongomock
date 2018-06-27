<template>
    <div class="x-data-entity">
        <div class="v-spinner-bg" v-if="loading"></div>
        <pulse-loader :loading="loading" color="#FF7D46" />
        <tabs v-if="!loading" @click="determineState">
            <tab title="General Data" id="generic" key="generic" :selected="true">
                <tabs :vertical="true">
                    <tab title="Basic Info" id="basic" key="basic" :selected="true">
                        <x-schema-list :data="entity.generic.basic" :schema="{type: 'array', items: fields.generic}"/>
                    </tab>
                    <tab v-for="item, i in entityGenericAdvanced" :title="item.title" :id="item.name" :key="item.name">
                        <x-schema-list :data="item.data" :schema="item.schema" />
                    </tab>
                </tabs>
            </tab>
            <tab title="Adapters Data" id="specific" key="specific">
                <tabs :vertical="true">
                    <tab v-for="item, i in sortedSpecificData" :id="item.id" :key="item.id" :selected="!i"
                         :title="item.plugin_name" :logo="true" :outdated="item.outdated">
                        <div class="d-flex content-header">
                            <div class="flex-expand server-info">Data From: {{ item.client_used }}</div>
                            <div v-if="viewBasic" @click="toggleView" class="link">View advanced</div>
                            <div v-if="!viewBasic" @click="toggleView" class="link">View basic</div>
                        </div>
                        <x-schema-list v-if="viewBasic" :data="item" :schema="adapterSchema(item.plugin_name)"/>
                        <tree-view :data="item.data.raw" :options="{rootObjectKey: 'raw', maxDepth: 1}" v-else/>
                    </tab>
                </tabs>
            </tab>
            <tab title="Extended Data" id="extended" key="extended">
                <tabs :vertical="true">
                    <tab v-for="item, i in entity.generic.data" :title="item.name" :id="`data_${i}`" :key="`data_${i}`"
                         :selected="!i">
                        <x-custom-data :data="item.data"/>
                    </tab>
                </tabs>
            </tab>
            <tab title="Tags" id="tags" key="tags">
                <div @click="activateTag" class="link tag-edit">Edit Tags</div>
                <div class="x-grid x-grid-col-2 w-lg">
                    <template v-for="label in entity.labels">
                        <div>{{ label }}</div>
                        <div class="link" @click="removeTag(label)">Remove</div>
                    </template>
                </div>
            </tab>
        </tabs>
        <x-tag-modal :module="module" :entities="entities" :tags="entity.labels" ref="tagModal" />
    </div>
</template>

<script>
	import Tabs from '../../components/tabs/Tabs.vue'
	import Tab from '../../components/tabs/Tab.vue'
	import xSchemaList from '../../components/schema/SchemaList.vue'
	import xCustomData from '../../components/schema/CustomData.vue'
	import xTagModal from '../../components/popover/TagModal.vue'
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_DATA_FIELDS, FETCH_DATA_BY_ID } from '../../store/actions'
	import { CHANGE_TOUR_STATE, UPDATE_TOUR_STATE } from '../../store/modules/onboarding'


    const lastSeenByModule = {
		'users': 'last_seen_in_devices',
        'devices': 'last_seen'
    }
	export default {
		name: 'x-data-entity',
        components: { Tabs, Tab, xSchemaList, xCustomData, xTagModal, PulseLoader },
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
                },
                tourState(state) {
                	return state.onboarding.tourStates.current
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
				return this.entity.specific.filter((item) => {
					if (item['plugin_type'] && item['plugin_type'].toLowerCase().includes('plugin')) return false

                    return true
				}).sort((first, second) => {
					// Adapters with no last_seen field go first
                    let firstSeen = first.data[lastSeenByModule[this.module]]
                    let secondSeen = second.data[lastSeenByModule[this.module]]
					if (!secondSeen) return 1
					if (!firstSeen) return -1
					// Turn strings into dates and subtract them to get a negative, positive, or zero value.
					return new Date(secondSeen) - new Date(firstSeen)
				}).map((item) => {
					item.id = `${item.plugin_unique_name}_${item.data.id}`
					if (lastSeen.has(item.plugin_name)) return { ...item, outdated: true }
					lastSeen.add(item.plugin_name)
					return item
				})
			},
            loading() {
            	return (!this.fields || !this.fields.generic || !this.fields.schema)
                    || (!this.entity || this.entity.internal_axon_id !== this.entityId)
            }
        },
        methods: {
            ...mapMutations({ changeState: CHANGE_TOUR_STATE, updateState: UPDATE_TOUR_STATE }),
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
			},
            toggleView() {
            	this.viewBasic = !this.viewBasic
            },
            adapterSchema(name) {
            	return {
            		type: 'array', items: [
                        { ...this.fields.schema.generic, name: 'data' },
                        { ...this.fields.schema.specific[name], name: 'data', title: 'SEPARATOR' }
					]
                }
            },
            determineState(tabId) {
            	if (tabId === 'specific') {
            	    this.changeState({ name: 'adapterDevice' })
                }
            }
        },
		created () {
			if (!this.fields || !this.fields.generic) {
				this.fetchDataFields({ module: this.module })
			}
			if (!this.entity || this.entity.internal_axon_id !== this.entityId) {
				this.fetchDataByID({ module: this.module, id: this.entityId })
			}
		},
        updated() {
			if (this.module === 'devices' && this.sortedSpecificData && this.sortedSpecificData.length) {
                this.changeState({ name: 'adaptersData' })
                this.updateState({
                    name: 'adapterDevice', id: this.sortedSpecificData[0].plugin_name, align: 'top'
                })
			}
        }
	}
</script>

<style lang="scss">
    .x-data-entity {
        position: relative;
        height: 100%;
        .x-tabs {
            width: 100%;
            height: 100%;
            .body {
                overflow: auto;
                height: calc(100% - 80px);
                .content-header {
                    padding-bottom: 4px;
                    margin-bottom: 16px;
                    border-bottom: 2px solid rgba($theme-orange, 0.4);
                    .server-info {
                        text-transform: uppercase;
                    }
                }
                .schema-list {
                    height: 100%;
                    overflow: auto;
                    .object {
                        width: calc(100% - 24px);
                    }
                }
                .specific .schema-list {
                    height: calc(100% - 36px);
                    > .array {
                        display: block;
                        > .item > .object > .array {
                            display: grid;
                            grid-template-columns: 50% 50%;
                            grid-gap: 12px 24px;
                            .separator {
                                grid-column-end: span 2;
                            }
                        }
                    }
                }
            }
            .tag-edit {
                text-align: right;
            }
        }
    }
</style>