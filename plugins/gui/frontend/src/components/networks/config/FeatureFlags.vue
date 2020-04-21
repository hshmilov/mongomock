<template>
  <div class="x-feature-flags tab-settings">
    <x-form
      :value="value"
      :schema="processedSchema"
      api-upload="settings/plugins/gui"
      @input="$emit('input', $event)"
      @validate="updateValidity"
    ></x-form>
    <div class="place-left">
      <x-button
        id="feature-flags-save"
        :disabled="!isValid"
        @click="$emit('save')"
      >Save</x-button>
    </div>
  </div>
</template>

<script>
  import xForm from '../../neurons/schema/Form.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import actionsMixin from '../../../mixins/actions'
  import {actionsMeta} from '../../../constants/enforcement'

  export default {
    name: 'XFeatureFlags',
    components: {
      xForm, xButton
    },
    mixins: [actionsMixin],
    props: {
      value: {
        type: Object,
        default: null
      },
      schema: {
        type: Object,
        required: true
      }
    },
    computed: {
      processedSchema() {
        if (!this.schema || !this.schema.items) return {}
        return { ...this.schema,
          items: this.schema.items.map(item => {
            if (item.name !== 'locked_actions') {
              return item
            }
            return { ...item,
              items: { ...item.items,
                enum: Object.keys(this.actionsDef).map(action => {
                  return {
                    name: action, title: actionsMeta[action].title
                  }
                })
              }
            }
          })
        }
      },
    },
    data() {
      return {
        isValid: true
      }
    },
    methods: {
      updateValidity(valid) {
        // Check that there is only one input to expiry or contract date - or none of them
        let valid_dates =   (this.value.expiry_date === '' ^ this.value.trial_end === '') ||
                        (this.value.expiry_date === '' && this.value.trial_end === '')
        this.isValid =  valid && valid_dates;
      }
    }
  }
</script>

<style lang="scss">
  .x-feature-flags {
    .x-array-edit {
      .object {
        width: 100%;
      }
    }
  }
</style>
