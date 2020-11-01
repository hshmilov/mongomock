<template>
  <XModal
    v-if="value"
    content-class="save-query-dialog"
    class="save-query-dialog"
    size="lg"
    approve-text="Save"
    :disabled="$v.$error"
    @close="onClose"
    @confirm="onConfirm"
  >
    <div
      v-if="value"
      slot="body"
    >
      <section class="form">
        <h3 class="modal-title">
          {{ modalTitle }}
        </h3>
        <div class="form-item">
          <label for="name">Query name</label>
          <span
            v-if="$v.queryFormProxies.name.$error"
            class="error-input"
          >
            {{ !$v.queryFormProxies.name.required
              ? 'Query name is a required field'
              : 'Query name is used by another query'
            }}
          </span>
          <input
            id="name"
            v-model="name"
            class="name-input"
            @keyup.enter="onConfirm"
            @keyup.esc="onClose"
          >
        </div>

        <div class="form-item">
          <label
            for="description"
          >Query description <span class="form-item--optional">optional</span>
          </label>
          <span
            v-if="$v.queryFormProxies.description.$error"
            class="error-input"
          >
            Description is limited to 300 chars
          </span>
          <textarea
            v-model="description"
            rows="5"
            name="description"
            @keyup.esc="onClose"
          />
        </div>

        <div
          class="form-item"
        >
          <ACheckbox
            id="private_query_checkbox"
            :checked="isPrivate"
            :disabled="userCannotAddSavedQueries || isEdit"
            @change="onChangePrivate"
          >
            Private query
          </ACheckbox>
        </div>
      </section>
    </div>
  </XModal>
</template>

<script>
import { mapActions } from 'vuex';
import { Checkbox } from 'ant-design-vue';
import { required, maxLength } from 'vuelidate/lib/validators';
import _get from 'lodash/get';
import _isNull from 'lodash/isNull';
import _isEmpty from 'lodash/isEmpty';

import XModal from '@axons/popover/Modal/index.vue';

import { SAVE_DATA_VIEW, FETCH_QUERY_INVALID_REFERENCES } from '@store/actions';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '@store/modules/onboarding';
import { SAVE_QUERY } from '@constants/getting-started';

import { fetchEntitySavedQueriesNames } from '@api/saved-queries';
import { getEntityPermissionCategory, EntitiesEnum as Entities } from '@constants/entities';

/**
   * @param {any} value - the input value to validate against
   *
   * @this {VueInstance} the component instance
   *
   * @description custom vuelidate validator - validates query names are unique
   *
   * @returns {Boolean} true if valid
   */
const uniqueQueryName = function uniqueQueryName(inputValue) {
  const newName = inputValue.toLocaleLowerCase();
  const initialName = (this.initialName || '').toLocaleLowerCase();
  // allow renaming a queryName to a different case
  if ((this.isEdit && newName === initialName) || _isEmpty(newName)) return true;
  // prevent using a queryName that's already been taken by another query
  return !this.existingQueriesNamesList.has(newName);
};

export default {
  name: 'XSaveModal',
  components: {
    XModal,
    ACheckbox: Checkbox,
  },
  model: {
    prop: 'value',
    event: 'closed',
  },
  props: {
    namespace: {
      type: String,
      required: true,
    },
    view: {
      type: Object,
      default: null,
    },
    value: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      queryFormProxies: {
        name: null,
        description: null,
        isPrivate: false,
      },
      existingQueriesNamesList: new Set(),
    };
  },
  validations: {
    queryFormProxies: {
      name: {
        required,
        uniqueQueryName,
      },
      description: {
        maxLength: maxLength(300),
      },
    },
  },
  computed: {
    isEdit() {
      return Boolean(this.view);
    },
    query() {
      return this.view || {};
    },
    permissionCategory() {
      return getEntityPermissionCategory(this.namespace);
    },
    userCannotAddSavedQueries() {
      return this.$cannot(this.permissionCategory,
        this.$permissionConsts.actions.Add, this.$permissionConsts.categories.SavedQueries);
    },
    name: {
      get() {
        if (this.isEdit) {
          const { name } = this.queryFormProxies;
          return !_isNull(name) ? name : this.query.name;
        }
        return this.queryFormProxies.name;
      },
      set(value) {
        this.queryFormProxies.name = value;
      },
    },
    description: {
      get() {
        if (this.isEdit) {
          const { description } = this.queryFormProxies;
          return !_isNull(description) ? description : this.query.description;
        }
        return this.queryFormProxies.description;
      },
      set(value) {
        this.queryFormProxies.description = value;
      },
    },
    isPrivate: {
      get() {
        const privateQueryEditMode = this.isEdit && this.query.private;
        if (privateQueryEditMode || this.userCannotAddSavedQueries) {
          return true;
        }
        return this.queryFormProxies.isPrivate;
      },
      set(value) {
        this.queryFormProxies.isPrivate = value;
      },
    },
    initialName() {
      return _get(this.query, 'name');
    },
    initialDescription() {
      return _get(this.query, 'description');
    },
    modalTitle() {
      return this.isEdit ? 'Update Query' : 'Save as a New Query';
    },
  },
  watch: {
    value(isOpen) {
      if (!isOpen) {
        return;
      }
      this.fetchQueriesNames();
      if (!this.isEdit) {
        return;
      }
      const { name } = this.queryFormProxies;
      const n = !_isNull(name) ? name : this.query.name;
      this.queryFormProxies.name = n;
    },
  },
  methods: {
    ...mapActions({
      saveView: SAVE_DATA_VIEW,
      milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION,
      fetchInvalidReferences: FETCH_QUERY_INVALID_REFERENCES,
    }),
    onClose() {
      this.resetForm();
      this.$emit('closed');
    },
    onChangePrivate() {
      this.isPrivate = !this.isPrivate;
    },
    resetForm() {
      this.queryFormProxies = {
        name: null,
        description: null,
        isPrivate: false,
      };
      this.$v.$reset();
    },
    hasFormDataChanged() {
      const namechanged = this.name !== this.initialName;
      const descriptionchanged = this.description !== this.initialDescription;

      return namechanged || descriptionchanged;
    },
    async onConfirm() {
      // validate on submission
      this.$v.queryFormProxies.$touch();

      if (this.hasFormDataChanged() && this.$v.$invalid) return;
      const uuid = await this.saveView({
        module: this.namespace,
        name: this.name,
        description: this.description,
        private: this.isPrivate,
        uuid: this.isEdit ? this.view.uuid : null,
      });

      if (uuid) {
        await this.fetchInvalidReferences({
          module: this.namespace,
          uuid,
        });
      }

      if (this.namespace === 'devices') {
        this.milestoneCompleted({ milestoneName: SAVE_QUERY });
      }
      this.fetchQueriesNames();
      this.onClose();
    },
    async fetchQueriesNames() {
      try {
        let names = await fetchEntitySavedQueriesNames(Entities[this.namespace]);
        names = names.filter((q) => q.name);
        names = names.map((q) => q.name.toLocaleLowerCase());
        this.existingQueriesNamesList = new Set(names);
      } catch (ex) {
        console.error(ex);
      }
    },
  },
};
</script>

<style lang="scss">
  $input-label-color: rgba(0,0,0,0.65);
  .save-query-dialog {
    .modal-container {
      max-height: 470px;
      .modal-body {
        overflow-y: hidden;
      }
    }
    .modal-body {
      padding: 20px 24px 32px 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;

      section {
        width: 100%;

        &.form {
        }
        .modal-title{
          font-size: 18px;
          margin :0 0 12px 0;
        }
        .form-item {
          display: flex;
          flex-direction: column;

          input, textarea {
            margin-bottom: 16px;
            resize: none;
            border-color:$grey-3;
            border-style: solid;
            border-width: 0.5px;
          }

          label {
            margin-bottom: 4px;
            color: $input-label-color;
          }

          .error-input {
            margin-bottom: 4px;
            color: #D0011B;
            font-size: 11px;
          }

          .name-input {
            height: 24px;
          }

          &--optional {
            font-size: 80%;
            color: $grey-4;
            display: inline-block;
            margin-left: 4px;
          }
        }
        &.actions {
          display: flex;
          justify-content: flex-end;
          .x-button {
            margin-left: 8px;
          }
        }
      }
    }
  }
</style>
