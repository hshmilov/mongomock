<template>
  <div class="x-action-config">
    <div class="header">
      <label for="action-name">Action Name:</label>
      <input
        id="action-name"
        ref="name"
        v-model="name"
        type="text"
        :disabled="disableName"
        :class="{disabled: disableName}"
      >
    </div>
    <div class="main">
      <template v-if="actionSchema && actionSchema.type">
        <h4 class="title">
          Configuration
        </h4>
        <x-form
          v-model="config"
          :schema="actionSchema"
          api-upload="actions"
          :read-only="readOnly"
          @validate="validateForm"
        />
      </template>
    </div>
    <div class="footer">
      <div class="error-text">
        {{ nameError || formError }}
      </div>
      <x-button
        v-if="!readOnly"
        :disabled="disableConfirm"
        @click="confirmAction"
      >Save</x-button>
    </div>
  </div>
</template>

<script>
  import xButton from '../../axons/inputs/Button.vue'
  import xForm from '../../neurons/schema/Form.vue'

  import actionsMixin from '../../../mixins/actions'

  export default {
    name: 'XActionConfig',
    components: {
      xButton, xForm
    },
    mixins: [actionsMixin],
    props: {
      value: {
        type: Object,
        default: () => {}
      },
      exclude: {
        type: Array,
        default: () => []
      },
      include: {
        type: Array,
        default: () => []
      },
      readOnly: Boolean
    },
    data () {
      return {
        nameValid: false,
        formValid: true
      }
    },
    computed: {
      disableConfirm () {
        return (!this.formValid || !this.nameValid)
      },
      disableName () {
        return this.value.uuid
      },
      name: {
        get () {
          if (!this.value) return ''
          return this.value.name
        },
        set (name) {
          this.$emit('input', {
            ...this.value,
            name, action: {
              ...this.value.action, config: this.config
            }
          })
        }
      },
      config: {
        get () {
          if (!this.value || !this.value.action.config) return this.actionConfig.default || {}
          return this.value.action.config
        },
        set (config) {
          this.$emit('input', {
            ...this.value,
            name: this.name, action: {
              ...this.value.action, config
            }
          })
        }
      },
      actionName () {
        if (!this.value || !this.value.action) return ''

        return this.value.action['action_name']
      },
      actionConfig () {
        if (!this.actionsDef || !this.actionName) return {}

        return this.actionsDef[this.actionName]
      },
      actionSchema () {
        if (!this.actionConfig) return {}

        return this.actionConfig.schema
      },
      formError () {
        if (this.formValid) return ''
        return 'Form has incomplete required fields'
      },
      nameError () {
        if (this.disableName) return ''
        if (this.name === '') {
          return 'Action Name is a required field'
        } else if ((this.actionNameExists(this.name) && !this.include.includes(this.name))
                || this.exclude.includes(this.name)) {
          return 'Name already taken by another saved Action'
        }
        return ''
      }
    },
    watch: {
      nameError (newVal) {
        this.nameValid = !newVal
      }
    },
    mounted () {
      this.$refs.name.focus()
      this.nameValid = !this.nameError
    },
    methods: {
      validateForm (valid) {
        this.formValid = valid
      },
      confirmAction () {
        this.$emit('confirm')
      }
    }
  }
</script>

<style lang="scss">
    .x-action-config {
        display: grid;
        grid-template-rows: 60px calc(100% - 108px) 48px;
        align-items: flex-start;
        .header {
            display: grid;
            grid-template-columns: 1fr 2fr;
            align-items: center;
            #action-name {
                margin-left: 12px;
                flex: 1 0 auto;
                &.disabled {
                    opacity: 0.6;
                }
            }
        }
        .main {
            overflow: auto;
            height: 100%;
            .title {
                margin-top: 0;
                margin-bottom: 12px;
            }
            .x-form .x-array-edit {
                grid-template-columns: 1fr;
                grid-gap: 24px 0;
            }
        }
        .footer {
            text-align: right;
            .error-text {
                min-height: 20px;
            }
        }
    }
</style>