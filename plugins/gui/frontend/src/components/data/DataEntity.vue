<template>
    <div class="x-data-entity">
        <div class="v-spinner-bg" v-if="loading"></div>
        <pulse-loader :loading="loading" color="#FF7D46" />
        <tabs v-if="!loading" @click="determineState" @updated="initTourState">
            <tab title="Adapters Data" id="specific" key="specific" v-if="!singleAdapter" :selected="true">
                <tabs :vertical="true">
                    <tab v-for="item, i in sortedSpecificData" :id="item.id" :key="item.id" :selected="!i"
                         :title="item.plugin_name" :logo="true" :outdated="item.outdated">
                        <div class="d-flex content-header">
                            <div class="flex-expand server-info">Data From: {{ item.client_used }}</div>
                            <button @click="toggleView" class="x-btn link">View {{viewBasic? 'advanced': 'basic'}}</button>
                        </div>
                        <x-schema-list v-if="viewBasic" :data="item" :schema="adapterSchema(item.plugin_name)" />
                        <tree-view :data="item.data.raw" :options="{rootObjectKey: 'raw', maxDepth: 1}" v-else />
                    </tab>
                </tabs>
            </tab>
            <tab title="General Data" id="generic" key="generic" :selected="singleAdapter">
                <tabs :vertical="true">
                    <tab title="Basic Info" id="basic" key="basic" :selected="true">
                        <x-schema-list :data="entity.generic.basic" :schema="{ type: 'array', items: fields.generic }"/>
                    </tab>
                    <tab v-for="item, i in entityGenericAdvancedRegular" :title="item.title" :id="item.name" :key="item.name">
                        <!-- For tabs representing a list of objects, show as a table -->
                        <x-schema-table v-if="tableView && item.schema.format && item.schema.format === 'table'"
                                 :data="item.data" :fields="item.schema.items.items" />
                        <x-schema-list :data="item.data" :schema="item.schema" v-else />
                    </tab>
                </tabs>
            </tab>
            <tab v-for="item in entityGenericAdvancedSpecial" :title="item.title" :id="item.name" :key="item.name">
                <x-schema-calendar v-if="item.schema.format && item.schema.format === 'calendar'" :data="item.data" />
            </tab>
            <tab title="Extended Data" id="extended" key="extended" v-if="entityExtendedData.length">
                <tabs :vertical="true">
                    <tab v-for="item, i in entityExtendedData" :title="item.name" :id="`data_${i}`" :key="`data_${i}`"
                         :selected="!i">
                        <x-custom-data :data="item.data"/>
                    </tab>
                </tabs>
            </tab>
            <tab title="Notes" id="notes" key="notes">
                <x-data-entity-notes :module="module" :entity-id="entityId" :data="entityNotes"
                                     :read-only="readOnly || history !== null" />
            </tab>
            <tab title="Tags" id="tags" key="tags">
                <div @click="activateTag" class="x-btn link tag-edit" :class="{ disabled: readOnly }">Edit Tags</div>
                <div class="x-grid x-grid-col-2 w-lg">
                    <template v-for="label in entity.labels">
                        <div>{{ label }}</div>
                        <div class="x-btn link" :class="{ disabled: readOnly }" @click="removeTag(label)">Remove</div>
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
    import xSchemaTable from '../schema/SchemaTable.vue'
    import xSchemaCalendar from '../schema/SchemaCalendar.vue'
    import xCustomData from '../../components/schema/CustomData.vue'
    import xTagModal from '../../components/popover/TagModal.vue'
    import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
    import xDataEntityNotes from './DataEntityNotes.vue'

    import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { SINGLE_ADAPTER } from '../../store/getters'
    import { FETCH_DATA_BY_ID } from '../../store/actions'
    import { CHANGE_TOUR_STATE, UPDATE_TOUR_STATE } from '../../store/modules/onboarding'

    const lastSeenByModule = {
		'users': 'last_seen_in_devices',
        'devices': 'last_seen'
    }
	export default {
		name: 'x-data-entity',
        components: {
		    Tabs, Tab, xSchemaList, xSchemaTable, xSchemaCalendar, xCustomData, xTagModal, PulseLoader, xDataEntityNotes
        },
        props: { module: { required: true }, readOnly: { default: false } },
		data () {
			return {
				viewBasic: true,
				entities: [ this.$route.params.id ],
				delayInitTourState: false
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
                },
                tableView(state) {
                	return state.configuration.data.system.tableView
                }
            }),
            ...mapGetters({ singleAdapter: SINGLE_ADAPTER }),
            entityId() {
				return this.$route.params.id
            },
            history() {
                if (this.$route.query.history === undefined) return null
				return this.$route.query.history
            },
			entityGenericAdvanced() {
				if (!this.entity.generic || !this.entity.generic.advanced) return []
				return this.entity.generic.advanced
                    .filter(item => item.data && (item.data.length || Object.keys(item.data).length))
                    .map((item) => {
                        let schema = this.getAdvancedFieldSchema(item.name) || {}
                        return { ...item,
                            title: schema.title,
                            schema: { ...schema, title: undefined }
                        }
                    })
			},
			entityGenericAdvancedRegular() {
				return this.entityGenericAdvanced.filter(item => item.schema.format !== 'calendar')
            },
            entityGenericAdvancedSpecial() {
            	return this.entityGenericAdvanced.filter(item => item.schema.format === 'calendar')
            },
			sortedSpecificData () {
				if (!this.entity.specific) return []
				let lastSeen = new Set()
				return this.entity.specific.filter((item) => {
				    if (item['hidden_for_gui']) return false
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
            entityExtendedData() {
                return this.entity.generic.data.filter(item => item.name !== 'Notes')
            },
            entityNotes() {
                let notes = this.entity.generic.data.find(item => item.name === 'Notes')
                if (!notes) return []
                return notes.data
            },
            loading() {
            	return (!this.fields || !this.fields.generic || !this.fields.schema)
                    || (!this.entity || this.entity.internal_axon_id !== this.entityId || this.entityDate !== this.historyDate)
            },
            entityDate() {
                if (!this.entity.accurate_for_datetime) return null
                return new Date(this.entity.accurate_for_datetime).toISOString().substring(0, 10)
            },
            historyDate() {
                if (!this.history) return null
                return this.history.substring(0, 10)
            }
        },
        watch: {
			entity(newEntity, oldEntity) {
                if (!this.delayInitTourState &&
                    (!oldEntity || oldEntity.internal_axon_id !== this.entityId)) {
                	// Indicate the tour state should be changed, once tabs are updated, so the element exists
					this.delayInitTourState = true
                }
            }
        },
        methods: {
            ...mapMutations({ changeState: CHANGE_TOUR_STATE, updateState: UPDATE_TOUR_STATE }),
            ...mapActions({
                fetchDataByID: FETCH_DATA_BY_ID
            }),
			getAdvancedFieldSchema(field) {
                let schema = this.fields.schema.generic.items.find(schema => schema.name === field)
                if (schema) return schema
				return Object.values(this.fields.schema.specific)[0].items.find(schema => schema.name === field)
			},
			removeTag (label) {
				if (!this.$refs || !this.$refs.tagModal ||this.readOnly) return
				this.$refs.tagModal.removeEntitiesLabels([label])
			},
			activateTag() {
				if (!this.$refs || !this.$refs.tagModal ||this.readOnly) return
				this.$refs.tagModal.activate()
			},
            toggleView() {
            	this.viewBasic = !this.viewBasic
            },
            adapterSchema(name, merged) {
            	let items = !merged? [
					{ type: 'array', ...this.fields.schema.generic, name: 'data', title: 'SEPARATOR' },
					{ type: 'array', ...this.fields.schema.specific[name], name: 'data', title: 'SEPARATOR' }
				]: [ ...this.fields.schema.generic.items, ...this.fields.schema.specific[name].items ]
            	return { type: 'array', items }
            },
            determineState(tabId) {
            	if (tabId === 'specific') {
            	    this.changeState({ name: 'adapterDevice' })
                }
            },
            initTourState() {
            	if (!this.delayInitTourState) return

                // Now is the time to change the tour's state
				if (this.module === 'devices' && this.sortedSpecificData && this.sortedSpecificData.length) {
					this.changeState({ name: 'adaptersData' })
					this.updateState({
						name: 'adapterDevice', id: this.sortedSpecificData[0].plugin_name, align: 'top'
					})
				}
				this.delayInitTourState = false
            }
        },
		created () {
			if (!this.entity || this.entity.internal_axon_id !== this.entityId || this.entityDate !== this.historyDate) {
				this.fetchDataByID({ module: this.module, id: this.entityId, history: this.history })
			} else {
				this.delayInitTourState = true
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
                    margin-bottom: 12px;
                    border-bottom: 2px solid rgba($theme-orange, 0.4);
                    .server-info {
                        text-transform: uppercase;
                    }
                }
                .schema-list {
                    height: 100%;
                    overflow: auto;
                    .object {
                        width: calc(100% - 36px);
                    }
                    >.x-array-view >.array {
                        display: grid;
                        grid-template-columns: 50% 50%;
                        grid-gap: 4px 0;
                        overflow-wrap: break-word;
                        .array {
                            margin-left: 20px;
                        }
                    }
                }
                .specific .schema-list {
                    height: calc(100% - 36px);
                    > .x-array-view > .array {
                        display: block;
                        > .item-container > .item > .object > .x-array-view > .array {
                            overflow-wrap: break-word;
                            display: grid;
                            grid-template-columns: 50% 50%;
                            grid-gap: 12px 24px;
                            margin-left: 0;
                            .array {
                                margin-left: 20px;
                            }
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