<template>
  <md-field v-if="readOnly">
    <md-input
      type="text"
      disabled
    />
  </md-field>
  <div
    v-else
    class="x-date-edit"
    :class="{labeled: label}"
  >
    <md-datepicker
      v-show="!hide || datepickerActive"
      ref="date"
      v-model="selectedDate"
      :md-disabled-dates="checkDisabled"
      :md-immediately="true"
      :md-debounce="500"
      :class="{'no-icon': minimal, 'no-clear': !clearable}"
    >
      <label v-if="label">{{ label }}</label>
    </md-datepicker>
    <x-button
      v-if="value && clearable"
      link
      @click="onClear"
    >X</x-button>
  </div>
</template>

<script>
  import xButton from '../../../../axons/inputs/Button.vue'

  export default {
    name: 'XDateEdit',
    components: {
      xButton
    },
    props: {
      value: {
        type: [String, Date],
        default: ''
      },
      readOnly: {
        type: Boolean, default: false
      },
      clearable: {
        type: Boolean, default: true
      },
      minimal: {
        type: Boolean, default: false
      },
      checkDisabled: {
        type: Function,
        default: () => false
      },
      label: {
        type: String,
        default: ''
      },
      hide: {
        type: Boolean,
        default: false
      }
    },
    computed: {
      selectedDate: {
        get () {
          return this.value
        },
        set (selectedDate) {
          if (selectedDate && typeof selectedDate !== 'string') {
            selectedDate.setMinutes(selectedDate.getMinutes() - selectedDate.getTimezoneOffset())
            selectedDate = selectedDate.toISOString().substring(0, 10)
          }
          if (this.value === selectedDate) return
          this.$emit('input', selectedDate)
        }
      },
      datepickerActive () {
        if (!this.$refs.date) return false
        return this.$refs.date.showDialog
      }
    },
    watch: {
      value (newValue) {
        if (!newValue) {
          this.onClear()
        }
      }
    },
    methods: {
      onClear () {
        this.$refs.date.modelDate = ''
        this.selectedDate = (typeof this.value === 'string')? '' : null
        this.$emit('clear')
      }
    }
  }
</script>

<style lang="scss">
    .x-date-edit {
        display: flex;
        .md-datepicker.md-clearable {
            .md-input-action {
                visibility: hidden;
            }
        }
        &:not(.labeled) .md-datepicker.md-field {
            width: auto;
            padding-top: 0;
            min-height: auto;
            margin-bottom: 0;
        }
        .x-button.link {
            margin-left: -16px;
            margin-bottom: 0;
            z-index: 100;
        }
    }
</style>