<template>
  <div class="x-entity-notes">
    <div class="header">
      <XSearchInput
        id="search-notes"
        v-model="searchValue"
        placeholder="Search notes..."
      />
      <div class="actions">
        <XButton
          v-if="selection && selection.length"
          type="link"
          @click="confirmRemoveNotes"
        >Delete</XButton>
        <XButton
          type="primary"
          :disabled="userCannotEditDevices"
          @click="createNote"
        >Add Note</XButton>
      </div>
    </div>
    <XTable
      v-model="selectedNotes"
      :data="noteData"
      :fields="noteFields"
      :sort="sort"
      :on-click-row="userCannotEditDevices? undefined : editNote"
      :on-click-col="sortNotes"
      :read-only="readOnlyNotes"
    />
    <XModal
      v-if="removeNoteModal.active"
      approve-text="Delete"
      @confirm="removeNotes"
      @close="closeRemoveNotesModal"
    >
      <div slot="body">
        You are about to delete {{ selection.length }} notes. Are you sure?
      </div>
    </XModal>
    <XModal
      v-if="configNoteModal.active"
      approve-text="Save"
      :title="noteModalTitle"
      @confirm="saveNote"
      @close="closeConfigNoteModal"
    >
      <template slot="body">
        <textarea
          v-model="configNoteModal.note"
          class="text-input"
          rows="4"
          placeholder="Enter your note..."
        />
      </template>
    </XModal>
    <XToast
      v-if="toastMessage"
      v-model="toastMessage"
    />
  </div>
</template>

<script>
import _get from 'lodash/get';
import { mapState, mapActions } from 'vuex';
import { getEntityPermissionCategory } from '@constants/entities';
import XSearchInput from '../../../neurons/inputs/SearchInput.vue';
import XTable from '../../../axons/tables/Table.vue';
import XModal from '../../../axons/popover/Modal/index.vue';
import XToast from '../../../axons/popover/Toast.vue';

import { SAVE_DATA_NOTE, REMOVE_DATA_NOTE } from '../../../../store/actions';

export default {
  name: 'XEntityNotes',
  components: {
    XSearchInput, XTable, XModal, XToast,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    entityId: {
      type: String,
      required: true,
    },
    notes: {
      type: Array,
      required: true,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      searchValue: '',
      sort: {
        field: 'accurate_for_datetime',
        desc: false,
      },
      selection: [],
      configNoteModal: {
        active: false,
        id: '',
        note: '',
      },
      removeNoteModal: {
        active: false,
      },
      toastMessage: '',
    };
  },
  computed: {
    ...mapState({
      currentUser(state) {
        const user = _get(state, 'auth.currentUser.data') || {};
        return {
          uuid: user.uuid,
          admin: user.admin || user.role_name === 'Admin',
        };
      },
    }),
    userCannotEditDevices() {
      return this.readOnly || this.$cannot(getEntityPermissionCategory(this.module),
        this.$permissionConsts.actions.Update);
    },
    selectedNotes: {
      get() {
        return this.userCannotEditDevices ? undefined : this.selection;
      },
      set(value) {
        this.selection = value;
      },
    },
    noteData() {
      return this.notes.filter((item) => {
        if (!this.searchValue) return true;
        const lowerSearchValue = this.searchValue.toLowerCase();
        return this.noteFields.find((field) => {
          if (field.type === 'string' && field.format === 'date-time') {
            return new Date(item[field.name]).toISOString().replace(/(T|Z)/g, ' ').includes(lowerSearchValue);
          }
          return item[field.name].toLowerCase().includes(lowerSearchValue);
        });
      }).sort((a, b) => {
        if (!this.sort.field) return 0;

        const valA = a[this.sort.field].toUpperCase();
        const valB = b[this.sort.field].toUpperCase();
        if (valA < valB) {
          return this.sort.desc ? -1 : 1;
        }
        if (valA > valB) {
          return this.sort.desc ? 1 : -1;
        }
        return 0;
      });
    },
    noteById() {
      return this.noteData.reduce((map, item) => {
        map[item.uuid] = item;
        return map;
      }, {});
    },
    noteFields() {
      return [
        { name: 'note', title: 'Note', type: 'string' },
        { name: 'user_name', title: 'User Name', type: 'string' },
        {
          name: 'accurate_for_datetime', title: 'Last Updated', type: 'string', format: 'date-time',
        },
      ];
    },
    noteModalTitle() {
      if (this.configNoteModal.id) {
        return 'Edit note';
      }
      return 'Add New Note';
    },
    readOnlyNotes() {
      if (this.$isAdmin()) return [];
      return this.noteData
        .filter((note) => note.user_id !== this.currentUser.uuid)
        .map((note) => note.uuid);
    },
  },
  methods: {
    ...mapActions({ saveDataNote: SAVE_DATA_NOTE, removeDataNote: REMOVE_DATA_NOTE }),
    createNote() {
      this.configNoteModal.active = true;
    },
    editNote(noteId) {
      if (this.selection.length) return;
      this.configNoteModal.active = true;
      this.configNoteModal.id = noteId;
      this.configNoteModal.note = this.noteById[noteId].note;
    },
    confirmRemoveNotes() {
      this.removeNoteModal.active = true;
    },
    closeRemoveNotesModal() {
      this.removeNoteModal.active = false;
    },
    removeNotes() {
      this.responseWrapper(this.removeDataNote({
        module: this.module,
        entityId: this.entityId,
        noteIdList: this.selection,
      }).then(() => {
        this.toastMessage = 'Notes were removed';
        this.selection = [];
        this.closeRemoveNotesModal();
      }));
    },
    saveNote() {
      this.responseWrapper(this.saveDataNote({
        module: this.module,
        entityId: this.entityId,
        noteId: this.configNoteModal.id,
        note: this.configNoteModal.note,
      }).then(() => {
        this.toastMessage = (this.configNoteModal.id ? 'Existing note was edited' : 'New note was created');
        this.closeConfigNoteModal();
      }));
    },
    closeConfigNoteModal() {
      this.configNoteModal.active = false;
      this.configNoteModal.id = '';
      this.configNoteModal.note = '';
    },
    responseWrapper(promise) {
      promise.catch((response) => {
        if (response.status === 400 && response.data) {
          // Some problem with the operation - usually permissions issue
          this.toastMessage = response.data.message;
        } else {
          // Last resort - should not happen to user!
          this.toastMessage = 'Operation could not be performed. Check your logs.';
        }
      });
    },
    sortNotes(fieldName) {
      if (this.sort.field !== fieldName) {
        this.sort.desc = true;
        this.sort.field = fieldName;
      } else if (this.sort.desc) {
        this.sort.desc = false;
      } else {
        this.sort.desc = true;
        this.sort.field = '';
      }
    },
  },
};
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

        .x-table {
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
