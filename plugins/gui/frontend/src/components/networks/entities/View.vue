<template>
    <div class="x-entity-view">
        <div class="v-spinner-bg" v-if="loading"></div>
        <pulse-loader :loading="loading" color="#FF7D46"/>
        <x-tabs v-show="!loading" @click="determineState" @updated="initTourState">
            <x-tab title="Adapters Data" id="specific" key="specific" v-if="!singleAdapter" :selected="true">
                <x-tabs :vertical="true">
                    <x-tab v-for="item, i in sortedSpecificData" :id="item.id" :key="i" :selected="!i"
                           :title="item.plugin_name" :logo="true" :outdated="item.outdated">
                        <div class="d-flex content-header">
                            <div class="flex-expand server-info">
                                <template v-if="item.client_used">
                                    Data From: {{ item.client_used }}
                                </template>
                            </div>
                            <button v-if="isGuiAdapterData(item)" @click="editFields" class="x-btn">Edit Fields</button>
                            <button v-else @click="toggleView" class="x-btn link">View {{viewBasic? 'advanced':
                                'basic'}}</button>
                        </div>
                        <x-list v-if="viewBasic || isGuiAdapterData(item)" :data="item"
                                :schema="adapterSchema(item.plugin_name)"/>
                        <tree-view :data="item.data.raw" :options="{rootObjectKey: 'raw', maxDepth: 1}" v-else/>
                    </x-tab>
                </x-tabs>
            </x-tab>
            <x-tab title="General Data" id="generic" key="generic" :selected="singleAdapter">
                <x-tabs :vertical="true" v-if="entity.generic && fields.generic">
                    <x-tab title="Basic Info" id="basic" key="basic" :selected="true">
                        <x-list :data="entity.generic.basic" :schema="{ type: 'array', items: fields.generic }"/>
                    </x-tab>
                    <x-tab v-for="item, i in entityGenericAdvancedRegular" :title="item.title" :id="item.name"
                           :key="item.name">
                        <!-- For tabs representing a list of objects, show as a table -->
                        <x-table v-if="tableView && item.schema.format && item.schema.format === 'table'"
                                 :data="item.data" :fields="item.schema.items"/>
                        <x-list :data="item.data" :schema="item.schema" v-else/>
                    </x-tab>
                </x-tabs>
            </x-tab>
            <x-tab v-for="item in entityGenericAdvancedSpecial" :title="item.title" :id="item.name" :key="item.name">
                <x-calendar v-if="item.schema.format && item.schema.format === 'calendar'" :data="item.data"/>
            </x-tab>
            <x-tab title="Extended Data" id="extended" key="extended" v-if="entityExtendedData.length">
                <x-tabs :vertical="true">
                    <x-tab v-for="item, i in entityExtendedData" :title="item.name" :id="`data_${i}`" :key="`data_${i}`"
                           :selected="!i">
                        <x-custom :data="item.data"/>
                    </x-tab>
                </x-tabs>
            </x-tab>
            <x-tab title="Notes" id="notes" key="notes">
                <x-notes :module="module" :entity-id="entityId" :data="entityNotes"
                         :read-only="readOnly || history !== null"/>
            </x-tab>
            <x-tab title="Tags" id="tags" key="tags">
                <div class="tag-edit">
                    <button @click="activateTag" class="x-btn link" :class="{disabled: readOnly}">Edit Tags</button>
                </div>
                <div class="x-grid x-grid-col-2 w-lg">
                    <template v-for="label in entity.labels">
                        <div>{{ label }}</div>
                        <div class="x-btn link" :class="{ disabled: readOnly }" @click="removeTag(label)">Remove</div>
                    </template>
                </div>
            </x-tab>
        </x-tabs>
        <x-tag-modal :module="module" :entities="{ids: entities, include: true}" :value="entity.labels" ref="tagModal"/>
        <x-modal v-if="fieldsEditor.active" @confirm="saveFieldsEditor" @close="closeFieldsEditor"
                 :disabled="!fieldsEditor.valid" approve-text="Save">
            <x-custom-fields slot="body" :module="module" v-model="fieldsEditor.data" :fields="customFields"
                             @validate="validateFieldsEditor"/>
        </x-modal>
        <x-toast v-if="toastMessage" :message="toastMessage" @done="removeToast"/>
    </div>
</template>

<script>
    import xTabs from '../../axons/tabs/Tabs.vue'
    import xTab from '../../axons/tabs/Tab.vue'
    import xList from '../../neurons/schema/List.vue'
    import xTable from '../../axons/tables/Table.vue'
    import xCalendar from '../../neurons/schema/Calendar.vue'
    import xCustom from '../../neurons/schema/Custom.vue'
    import xModal from '../../axons/popover/Modal.vue'
    import xTagModal from '../../neurons/popover/TagModal.vue'
    import xNotes from './Notes.vue'
    import xCustomFields from './CustomFields.vue'
    import xToast from '../../axons/popover/Toast.vue'
    import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

    import {mapState, mapGetters, mapMutations, mapActions} from 'vuex'
    import {SINGLE_ADAPTER} from '../../../store/getters'
    import {FETCH_DATA_BY_ID, SAVE_CUSTOM_DATA, FETCH_DATA_FIELDS, FETCH_DATA_HYPERLINKS} from '../../../store/actions'
    import {CHANGE_TOUR_STATE, UPDATE_TOUR_STATE} from '../../../store/modules/onboarding'
    import {guiPluginName, initCustomData} from '../../../constants/entities'

    const lastSeenByModule = {
        'users': 'last_seen_in_devices',
        'devices': 'last_seen'
    }
    export default {
        name: 'x-entity-view',
        components: {
            xTabs, xTab, xList, xTable, xCalendar, xCustom,
            xModal, xTagModal, xNotes, xCustomFields, xToast, PulseLoader
        },
        props: {module: {required: true}, readOnly: {default: false}},
        data() {
            return {
                viewBasic: true,
                entities: [this.$route.params.id],
                delayInitTourState: false,
                fieldsEditor: {active: false},
                toastMessage: ''
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
                },
                fetchingData(state) {
                    return state[this.module].current.fetching || state[this.module].fields.fetching
                }
            }),
            ...mapGetters({singleAdapter: SINGLE_ADAPTER}),
            entityId() {
                return this.$route.params.id
            },
            history() {
                if (this.$route.query.history === undefined) return null
                return this.$route.query.history
            },
            entityGenericAdvanced() {
                if (!this.entity.generic || !this.entity.generic.advanced || !this.fields || !this.fields.generic)
                    return []
                return this.entity.generic.advanced
                    .filter(item => item.data && (item.data.length || Object.keys(item.data).length))
                    .map(item => {
                        let schema = this.fields.generic.find(schema => schema.name.match(`\\.${item.name}$`)) || {}
                        item.title = schema.title
                        schema.title = undefined
                        if (Array.isArray(schema.items)) {
                            schema.items = schema.items.filter(field =>
                                !field.name.includes('raw') && (!field.items || !Array.isArray(field.items)))
                        }
                        return {...item, schema}
                    })
            },
            entityGenericAdvancedRegular() {
                return this.entityGenericAdvanced.filter(item => item.schema.format !== 'calendar')
            },
            entityGenericAdvancedSpecial() {
                return this.entityGenericAdvanced.filter(item => item.schema.format === 'calendar')
            },
            sortedSpecificData() {
                if (!this.entity.specific) return []
                let lastSeen = new Set()
                let res = this.entity.specific.filter((item) => {
                    if (item['hidden_for_gui']) return false
                    if (item['plugin_type'] && item['plugin_type'].toLowerCase().includes('plugin')) return false

                    return true
                }).sort((first, second) => {
                    // GUI plugin (miscellaneous) always comes last
                    if (first.plugin_name === guiPluginName) return 1
                    if (second.plugin_name === guiPluginName) return -1

                    // Adapters with no last_seen field go first
                    let firstSeen = first.data[lastSeenByModule[this.module]]
                    let secondSeen = second.data[lastSeenByModule[this.module]]
                    if (!secondSeen) return 1
                    if (!firstSeen) return -1
                    // Turn strings into dates and subtract them to get a negative, positive, or zero value.
                    return new Date(secondSeen) - new Date(firstSeen)
                }).map((item) => {
                    item.id = `${item.plugin_unique_name}_${item.data.id}`
                    if (lastSeen.has(item.plugin_name)) return {...item, outdated: true}
                    lastSeen.add(item.plugin_name)
                    return item
                })
                if (res[res.length - 1].plugin_name !== guiPluginName) {
                    // Add initial gui adapters data
                    res.push(initCustomData(this.module))
                }
                return res
            },
            entityExtendedData() {
                if (!this.entity.generic || !this.entity.generic.data) return []
                return this.entity.generic.data.filter(item => item.name !== 'Notes')
            },
            entityNotes() {
                if (!this.entity.generic || !this.entity.generic.data) return []
                let notes = this.entity.generic.data.find(item => item.name === 'Notes')
                if (!notes) return []
                return notes.data
            },
            loading() {
                return this.fetchingData || !this.fields || !this.fields.generic || !this.fields.schema
                    || !this.entity || this.entity.internal_axon_id !== this.entityId
                    || this.entityDate !== this.historyDate
            },
            entityDate() {
                if (!this.entity.accurate_for_datetime) return null
                return new Date(this.entity.accurate_for_datetime).toISOString().substring(0, 10)
            },
            historyDate() {
                if (!this.history) return null
                return this.history.substring(0, 10)
            },
            customFields() {
                return (this.fields.specific.gui || this.fields.generic)
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
            ...mapMutations({
                changeState: CHANGE_TOUR_STATE, updateState: UPDATE_TOUR_STATE
            }),
            ...mapActions({
                fetchDataByID: FETCH_DATA_BY_ID, saveCustomData: SAVE_CUSTOM_DATA, fetchDataFields: FETCH_DATA_FIELDS,
                fetchDataHyperlinks: FETCH_DATA_HYPERLINKS
            }),
            fetchCurrentEntity() {
                this.fetchDataByID({module: this.module, id: this.entityId, history: this.history})
            },
            removeTag(label) {
                if (!this.$refs || !this.$refs.tagModal || this.readOnly) return
                this.$refs.tagModal.removeEntitiesLabels([label])
            },
            activateTag() {
                if (!this.$refs || !this.$refs.tagModal || this.readOnly) return
                this.$refs.tagModal.activate()
            },
            toggleView() {
                this.viewBasic = !this.viewBasic
            },
            adapterSchema(name) {
                if (!this.fields || !this.fields.schema) return {}
                let items = [{
                    type: 'array', ...this.fields.schema.generic,
                    name: 'data', title: 'SEPARATOR', path: [this.module, 'aggregator']
                }, {
                    type: 'array', ...this.fields.schema.specific[name],
                    name: 'data', title: 'SEPARATOR', path: [this.module, name]
                }]
                if (name === guiPluginName) {
                    items[0].items = items[0].items.filter(item => item.name !== 'id')
                }
                return {type: 'array', items}
            },
            determineState(tabId) {
                if (tabId === 'specific') {
                    this.changeState({name: 'adapterDevice'})
                }
            },
            initTourState() {
                if (!this.delayInitTourState) return

                // Now is the time to change the tour's state
                if (this.module === 'devices' && this.sortedSpecificData && this.sortedSpecificData.length) {
                    this.changeState({name: 'adaptersData'})
                    this.updateState({
                        name: 'adapterDevice', id: this.sortedSpecificData[0].plugin_name, align: 'top'
                    })
                }
                this.delayInitTourState = false
            },
            isGuiAdapterData(data) {
                return data.plugin_name === guiPluginName
            },
            flattenObj(path, obj) {
                if (Array.isArray(obj)) {
                    return this.flattenObj(path, obj[0])
                }
                if (typeof obj === 'object' && Object.keys(obj).length) {
                    return Object.keys(obj).reduce((map, key) => {
                        return {...map, ...this.flattenObj(path ? `${path}.${key}` : key, obj[key])}
                    }, {})
                }
                return {[path]: obj}
            },
            editFields() {
                this.fieldsEditor = {
                    active: true,
                    data: this.flattenObj('', this.sortedSpecificData[this.sortedSpecificData.length - 1].data || {}),
                    valid: true
                }
            },
            saveFieldsEditor() {
                if (!this.fieldsEditor.valid) return
                this.saveCustomData({
                    module: this.module, data: {
                        selection: {
                            ids: this.entities, include: true
                        }, data: this.fieldsEditor.data
                    }
                }).then((response) => {
                    if (response.status === 200) {
                        this.toastMessage = 'Saved Custom Data'
                        this.fetchDataFields({module: this.module})
                        this.fetchCurrentEntity()
                        this.closeFieldsEditor()
                    } else {
                        this.toastMessage = response.data.message
                    }
                })
            },
            closeFieldsEditor() {
                this.fieldsEditor = {active: false}
            },
            validateFieldsEditor(valid) {
                this.fieldsEditor.valid = valid
            },
            removeToast() {
                this.toastMessage = ''
            }
        },
        created() {
            this.fetchDataHyperlinks({ module: this.module})
            if (!this.entity || this.entity.internal_axon_id !== this.entityId || this.entityDate !== this.historyDate) {
                this.fetchCurrentEntity()
            } else {
                this.delayInitTourState = true
            }
        }
    }
</script>

<style lang="scss">
    .x-entity-view {
        position: relative;
        height: 100%;

        .x-tabs {
            width: 100%;
            height: 100%;

            .body {
                .content-header {
                    padding-bottom: 4px;
                    margin-bottom: 12px;
                    border-bottom: 2px solid rgba($theme-orange, 0.4);

                    .server-info {
                        text-transform: uppercase;
                    }
                }

                .x-list {
                    height: 100%;
                    overflow: auto;

                    .object {
                        width: calc(100% - 36px);
                    }

                    > .x-array-view > .array {
                        display: grid;
                        grid-template-columns: 50% 50%;
                        grid-gap: 4px 0;
                        overflow-wrap: break-word;

                        .array {
                            margin-left: 20px;
                        }
                    }
                }

                .specific .x-list {
                    height: calc(100% - 36px);
                    white-space: pre;

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

            .tag-edit .x-btn {
                text-align: right;
            }
        }
    }
</style>
