<template>
    <div class="x-entity-notes">
        <div class="header">
            <x-search-input v-model="searchValue" placeholder="Search Notes..." id="search-notes"/>
            <div class="actions">
                <button class="x-btn link" v-if="selectedNotes && selectedNotes.length" @click="confirmRemoveNotes">Remove</button>
                <button class="x-btn" @click="readOnly? undefined : createNote()" :class="{disabled: readOnly}">+ Note</button>
            </div>
        </div>
        <x-table :data="noteData" :fields="noteSchema" :sort="sort" id-field="uuid"
                 v-model="readOnly? undefined : selectedNotes"
                 :click-row-handler="readOnly? undefined : editNote" :click-col-handler="sortNotes"
                 :read-only="readOnlyNotes"/>
        <x-modal v-if="removeNoteModal.active" approve-text="Delete" @confirm="removeNotes"
                 @close="closeRemoveNotesModal">
            <div slot="body">You are about to remove {{selectedNotes.length}} notes. Are you sure?</div>
        </x-modal>
        <x-modal v-if="configNoteModal.active" approve-text="Save" @confirm="saveNote" @close="closeConfigNoteModal"
                 :title="noteModalTitle">
            <template slot="body">
                <textarea v-model="configNoteModal.note" class="text-input" rows="4"
                          placeholder="Enter your note..."></textarea>
            </template>
        </x-modal>
        <x-toast v-if="toastMessage" :message="toastMessage" @done="remoteToast"/>
    </div>
</template>

<script>
    import xSearchInput from '../../neurons/inputs/SearchInput.vue'
    import xTable from '../../axons/tables/Table.vue'
    import xModal from '../../axons/popover/Modal.vue'
    import xToast from '../../axons/popover/Toast.vue'

    import {mapState, mapActions} from 'vuex'
    import {SAVE_DATA_NOTE, REMOVE_DATA_NOTE} from '../../../store/actions'

    export default {
        name: 'x-entity-notes',
        components: {xSearchInput, xTable, xModal, xToast},
        props: {
            module: {required: true}, entityId: {required: true}, data: {required: true},
            readOnly: {default: false}
        },
        computed: {
            ...mapState({
                currentUser(state) {
                    return {
                        uuid: state.auth.currentUser.data.uuid,
                        admin: state.auth.currentUser.data.admin || state.auth.currentUser.data.role_name === 'Admin'
                    }
                }
            }),
            noteData() {
                return this.data.filter(item => {
                    if (!this.searchValue) return true
                    let lowerSearchValue = this.searchValue.toLowerCase()
                    return this.noteSchema.find(field => {
                        if (field.type === 'string' && field.format === 'date-time') {
                            return new Date(item[field.name]).toISOString().replace(/(T|Z)/g, ' ').includes(lowerSearchValue)
                        }
                        return item[field.name].toLowerCase().includes(lowerSearchValue)
                    })
                }).sort((a, b) => {
                    if (!this.sort.field) return 0

                    let valA = a[this.sort.field].toUpperCase()
                    let valB = b[this.sort.field].toUpperCase()
                    if (valA < valB) {
                        return this.sort.desc ? -1 : 1
                    }
                    if (valA > valB) {
                        return this.sort.desc ? 1 : -1
                    }
                    return 0
                })
            },
            noteById() {
                return this.noteData.reduce((map, item) => {
                    map[item.uuid] = item
                    return map
                }, {})
            },
            noteSchema() {
                return [
                    {name: 'note', title: 'Note', type: 'string'},
                    {name: 'user_name', title: 'User Name', type: 'string'},
                    {name: 'accurate_for_datetime', title: 'Last Updated', type: 'string', format: 'date-time'}
                ]
            },
            noteModalTitle() {
                if (this.configNoteModal.id) {
                    return 'Edit note'
                } else {
                    return 'Add new note'
                }
            },
            readOnlyNotes() {
                if (this.currentUser.admin) return []
                return this.noteData
                    .filter(note => note['user_id'] !== this.currentUser.uuid)
                    .map(note => note.uuid)
            }
        },
        data() {
            return {
                searchValue: '',
                sort: {
                    field: 'accurate_for_datetime',
                    desc: false
                },
                selectedNotes: [],
                configNoteModal: {
                    active: false,
                    id: '',
                    note: ''
                },
                removeNoteModal: {
                    active: false
                },
                toastMessage: ''
            }
        },
        methods: {
            ...mapActions({saveDataNote: SAVE_DATA_NOTE, removeDataNote: REMOVE_DATA_NOTE}),
            createNote() {
                this.configNoteModal.active = true
            },
            editNote(noteId) {
                if (this.selectedNotes.length) return
                this.configNoteModal.active = true
                this.configNoteModal.id = noteId
                this.configNoteModal.note = this.noteById[noteId].note
            },
            confirmRemoveNotes() {
                this.removeNoteModal.active = true
            },
            closeRemoveNotesModal() {
                this.removeNoteModal.active = false
            },
            removeNotes() {
                this.responseWrapper(this.removeDataNote({
                    module: this.module,
                    entityId: this.entityId,
                    noteIdList: this.selectedNotes
                }).then(() => {
                    this.toastMessage = 'Notes were removed'
                    this.selectedNotes = []
                    this.closeRemoveNotesModal()
                }))
            },
            saveNote() {
                this.responseWrapper(this.saveDataNote({
                    module: this.module,
                    entityId: this.entityId,
                    noteId: this.configNoteModal.id,
                    note: this.configNoteModal.note
                }).then(() => {
                    this.toastMessage = (this.configNoteModal.id ? 'Existing note was edited' : 'New note was created')
                    this.closeConfigNoteModal()
                }))
            },
            closeConfigNoteModal() {
                this.configNoteModal.active = false
                this.configNoteModal.id = ''
                this.configNoteModal.note = ''
            },
            responseWrapper(promise) {
                promise.catch(response => {
                    if (response.status === 400 && response.data) {
                        // Some problem with the operation - usually permissions issue
                        this.toastMessage = response.data.message
                    } else {
                        // Last resort - should not happen to user!
                        this.toastMessage = 'Operation could not be performed. Check your logs.'
                    }
                })
            },
            remoteToast() {
                this.toastMessage = ''
            },
            sortNotes(fieldName) {
                if (this.sort.field !== fieldName) {
                    this.sort.desc = true
                    this.sort.field = fieldName
                } else if (this.sort.desc) {
                    this.sort.desc = false
                } else {
                    this.sort.desc = true
                    this.sort.field = ''
                }
            }
        }
    }
</script>

<style lang="scss">
    .x-entity-notes {
        .header {
            display: flex;
            margin-bottom: 12px;

            .x-search-input {
                width: 400px;
            }

            .actions {
                flex: 1 0 auto;
                display: flex;
                justify-content: flex-end;
            }
        }

        .x-striped-table {
            th:nth-child(3) {
                width: 200px;
            }

            th:nth-child(4) {
                width: 160px;
            }

            td:nth-child(2) {
                white-space: pre-line;
            }
        }

        .modal-body {
            .text-input {
                width: calc(100% - 6px);
            }
        }
    }
</style>