<template>
  <v-dialog
    :value="value"
    content-class="save-query-dialog"
    class="save-query-dialog"
    max-width="500"
    persistent
    @input="dialogStateChanged"
    @keydown.esc="onClose"
  >
    <v-card v-if="value">
      <section class="form">
        <div class="form-item">
          <label for="name">Query Name</label>
          <span
            v-if="$v.queryFormProxies.name.$error"
            class="error-input"
          >{{ !$v.queryFormProxies.name.required ? 'Query Name is a required field' : 'Query Name is used by another query' }}</span>
          <input
            id="name"
            v-model="name"
            class="name-input"
            @keyup.enter="onConfirm"
          >
        </div>

        <div class="form-item">
          <label for="description">Query Description</label>
          <span
            v-if="$v.queryFormProxies.description.$error"
            class="error-input"
          >Description is limited to 300 chars</span>
          <textarea
            v-model="description"
            rows="5"
            name="description"
            @keyup.enter="onConfirm"
          />
        </div>
      </section>

      <section class="actions">
        <x-button 
          link 
          @click="onClose"
        >Cancel</x-button>
        <x-button 
          :disabled="$v.$error" 
          @click="onConfirm"
        >Save</x-button>
      </section>
    </v-card>
  </v-dialog>
</template>

<script>
  import {mapActions} from 'vuex'
  import { required, maxLength } from 'vuelidate/lib/validators'
  import _get from 'lodash/get'
  import _isNull from 'lodash/isNull'
  import _isEmpty from 'lodash/isEmpty'

  import xButton from '@axons/inputs/Button.vue'

  import {SAVE_DATA_VIEW} from '@store/actions'
  import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '@store/modules/onboarding';
  import { SAVE_QUERY } from '@constants/getting-started'

  import { featchEntityTags, featchEntitySavedQueriesNames } from '@api/saved-queries'
  import { EntitiesEnum as Entities } from '@constants/entities'
  
  /**
   * @param {any} value - the input value to validate against
   * 
   * @this {VueInstance} the component instance
   * 
   * @description custom vuelidate validator - validates query names are unique
   * 
   * @returns {Boolean} true if valid
   */
  const uniqueQueryName = function(inputValue) {
    if ((this.isEdit && inputValue === this.initialName) || _isEmpty(inputValue)) return true
    return !this.existingQueriesNamesList.has(inputValue.toLocaleLowerCase())
  }

  export default {
    name: 'XSaveModal',
    components: {
      xButton
    },
    model: {
    prop: "value",
    event: "closed"
    },
    props: {
      namespace: {
        type: String,
        required: true
      },
      view: {
        type: Object,
        default: null
      },
      value: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        queryFormProxies: {
          name: null,
          description: null
        },
        existingQueriesNamesList: new Set()
      }
    },
    validations: {
      queryFormProxies: {
        name: {
          required,
          uniqueQueryName
        },
        description: {
          maxLength: maxLength(300)
        }
      }
    },
    computed: {
      isEdit () {
        return Boolean(this.view)
      },
      query() {
        return this.view || {}
      },
      name: {
        get() {
          if(this.isEdit) {
            const { name } = this.queryFormProxies
            return !_isNull(name) ? name : this.query.name
          }
          return this.queryFormProxies.name
        },
        set(value) {
          this.queryFormProxies.name = value
        }
      },
      description: {
        get() {
          if(this.isEdit) {
            const { description } = this.queryFormProxies
            return !_isNull(description) ? description : this.query.description
          }
          return this.queryFormProxies.description
        },
        set(value) {
          this.queryFormProxies.description = value
        }
      },
      initialName() {
        return _get(this.query, 'name')
      },
      initialDescription() {
        return _get(this.query, 'description')
      },
    },
    created() {
      this.fetchQueriesNames()
    },
    methods: {
      ...mapActions({
        saveView: SAVE_DATA_VIEW,
        milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION,
      }),
      dialogStateChanged(isOpen) {
        if (!isOpen) {
          // when save modal closed, reset the queryFormProxies and the form validation state
          this.$v.queryFormProxies.$reset()
          this.queryFormProxies = {
            name: null,
            description: null
          }
        } else {
          // when the save modal opened, (if in edit mode) init the queryFormProxies so validation will work as expected
          if (this.isEdit) {
            this.queryFormProxies.name = this.query.name
            this.queryFormProxies.description = this.query.description
          }
        }
      },
      onClose () {
        this.resetForm()
        this.$emit('closed')
      },
      resetForm() {
        this.queryFormProxies = {
          name: null,
          description: null
        }
        this.$v.$reset()
      },
      hasFormDataChanged() {
        const namechanged = this.name !== this.initialName
        const descriptionchanged = this.description !== this.initialDescription

        return namechanged || descriptionchanged
      },
      onConfirm () {
        // validate on submission
        this.$v.$touch()
        if (this.hasFormDataChanged() && this.$v.$invalid) return

        this.saveView({
          module: this.namespace,
          name: this.name,
          description: this.description,
          uuid: this.isEdit? this.view.uuid : null
        }).then(() => {
          if (this.namespace === 'devices') {
            this.milestoneCompleted({ milestoneName: SAVE_QUERY })
          }
          this.fetchQueriesNames()
          this.onClose()
        })
      },
      async fetchQueriesNames() {
        try {
          let names = await featchEntitySavedQueriesNames(Entities[this.namespace])
          names = names.filter(q => q.name)
          names = names.map(q => q.name.toLocaleLowerCase())
          this.existingQueriesNamesList = new Set(names)
        } catch (ex) {
          console.error(ex)
        }
      },
    },
  }
</script>

<style lang="scss">
  .v-overlay--active {
    z-index: 1001 !important;
  }
  .v-dialog__content--active {
    z-index: 1002 !important;
  }
  .save-query-dialog {
    .v-card {
      min-height: 309px;
      width: 500px;
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