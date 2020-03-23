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
          />
        </div>
      </section>
    </div>
  </XModal>
</template>

<script>
import { mapActions } from 'vuex';
import { required, maxLength } from 'vuelidate/lib/validators';
import _get from 'lodash/get';
import _isNull from 'lodash/isNull';
import _isEmpty from 'lodash/isEmpty';

import XModal from '@axons/popover/Modal.vue';

import { SAVE_DATA_VIEW } from '@store/actions';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '@store/modules/onboarding';
import { SAVE_QUERY } from '@constants/getting-started';

import { fetchEntitySavedQueriesNames } from '@api/saved-queries';
import { EntitiesEnum as Entities } from '@constants/entities';

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
  if ((this.isEdit && inputValue === this.initialName) || _isEmpty(inputValue)) return true;
  return !this.existingQueriesNamesList.has(inputValue.toLocaleLowerCase());
};

export default {
  name: 'XSaveModal',
  components: {
    XModal,
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
    initialName() {
      return _get(this.query, 'name');
    },
    initialDescription() {
      return _get(this.query, 'description');
    },
  },
  watch: {
    value(isOpen) {
      if (isOpen && this.isEdit) {
        const { name } = this.queryFormProxies;
        const n = !_isNull(name) ? name : this.query.name;
        this.queryFormProxies.name = n;
      }
    },
  },
  created() {
    this.fetchQueriesNames();
  },
  methods: {
    ...mapActions({
      saveView: SAVE_DATA_VIEW,
      milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION,
    }),
    onClose() {
      this.resetForm();
      this.$emit('closed');
    },
    resetForm() {
      this.queryFormProxies = {
        name: null,
        description: null,
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
      await this.saveView({
        module: this.namespace,
        name: this.name,
        description: this.description,
        uuid: this.isEdit ? this.view.uuid : null,
      });

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
  .v-overlay--active {
    z-index: 1001 !important;
  }
  .v-dialog__content--active {
    z-index: 1002 !important;
  }
  .save-query-dialog {
    .modal-container {
      max-height: 360px;
    }
    .modal-body {
      padding: 20px 24px 32px 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;

      section {
        width: 100%;

        &.form {
          margin-bottom: 32px;
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
