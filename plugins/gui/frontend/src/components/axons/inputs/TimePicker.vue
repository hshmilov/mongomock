<template>
  <v-menu
    ref="menu"
    v-model="timeModal"
    :close-on-content-click="false"
    :nudge-right="40"
    transition="scale-transition"
    offset-y
    offset-overflow
    class="x-time-picker"
  >
    <template v-slot:activator="{ on }">
      <div class="time-picker-text">
        <label v-if="label">{{ label }}</label>
        <v-text-field
          :value="formattedTime()"
          :error="error"
          :read-only="readOnly"
          @change="onInput"
          v-on="on"
        />
      </div>
    </template>
    <v-time-picker
      v-if="timeModal && !readOnly"
      v-model="timeValue"
      :ampm-in-title="true"
      :landscape="true"
      @click:minute="$refs.menu.save(value)"
    />
  </v-menu>
</template>

<script>
    import moment from 'moment'

    export default {
        name: 'XTimePicker',
        props: {
            value: {
                type: String,
                default: ''
            },
            readOnly: {
                type: Boolean, default: false
            },
            label: {
                type: String,
                default: ''
            }
        },
        data() {
          return {
              timeModal: false,
              error: false
          }
        },
        computed: {
            timePickerActive () {
                if (!this.$refs.time) return false
                return this.$refs.time.showDialog
            },
            timeValue: {
                get() {
                    return this.value
                },
                set(value) {
                    this.error = false
                    this.$emit('input', value)
                    this.$emit('validate', true)
                }

            }
        },
        methods: {
            formattedTime() {
                return moment(this.value, 'HH:mm').format('h:mma')
            },
            onInput (selectedTime) {
                let time = moment(selectedTime, 'h:mma');
                if(!time.isValid()){
                    this.error = true
                    this.$emit('validate', false)
                    return;
                }
                this.error = false

                this.$emit('input', time.format('HH:mm'))
                this.$emit('validate', true)
            }
        }
    }
</script>

<style lang="scss">
  .time-picker-text {
    .x-button.link {
      margin-left: -16px;
      margin-bottom: 0;
      z-index: 100;
    }

    input {
      font-size: 14px;
      padding-left: 3px;
    }
  }
</style>