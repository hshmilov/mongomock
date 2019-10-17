<template>
  <div
    class="x-checkbox"
    :class="{
      checked,
      disabled: readOnly
    }"
    @click.stop="clickCheckbox"
    @keyup.enter.stop="clickCheckbox"
  >
    <div
      class="container"
      :class="{ indeterminate }"
    >
      <input
        ref="checkbox"
        v-model="checked"
        type="checkbox"
        :disabled="readOnly"
      >
    </div>
    <slot>
      <label
        v-if="label"
        class="label"
      >{{ label }}</label>
    </slot>
  </div>
</template>

<script>
  export default {
    name: 'XCheckbox',
    model: {
      prop: 'data',
      event: 'change'
    },
    props: {
      data: {
        type: [Array, Boolean, String],
        default: false
      },
      value: {
        type: String,
        default: 'on'
      },
      label: {
        type: String,
        default: ''
      },
      indeterminate: {
        type: Boolean,
        default: false
      },
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    computed: {
      checked: {
        get () {
          if (Array.isArray(this.data) && !Array.isArray(this.value)) {
            return this.data.includes(this.value)
          } else if (typeof this.data === 'boolean') {
            return this.indeterminate || this.data === true
          } else {
            return this.data === this.value
          }
        },
        set (checked) {
          this.updateData(checked)
        }
      }
    },
    methods: {
      change (data) {
        this.$emit('change', data)
      },
      updateData (checked) {
        if (Array.isArray(this.data) && !Array.isArray(this.value)) {
          if (checked) {
            this.change(this.data.concat([this.value]))
            return
          }
          let index = this.data.indexOf(this.value)
          if (index > -1) {
            let temp = [...this.data]
            temp.splice(index, 1)
            this.change(temp)
          }
        } else if (typeof this.data === 'boolean') {
          this.change(checked)
        } else {
          this.change(checked ? this.value : (Array.isArray(this.data) ? [] : null))
        }
      },
      clickCheckbox () {
        this.$refs.checkbox.click()
      }
    }
  }
</script>

<style lang="scss">
    .x-checkbox {
        cursor: pointer;

        &.disabled {
            cursor: default;
            opacity: 0.6;

            .container:hover {
                border-color: $grey-3;
            }

            &.checked .container:hover {
                border-color: $grey-5;
            }

          .label {
            cursor: default;

            &:hover {
              text-shadow: none;
            }
          }
        }

        &.checked .container {
          background-color: $grey-5;
          border-color: $grey-5;

          &:after {
            opacity: 1;
            transform: rotate(45deg) scale3D(1, 1, 1);
            transition: .4s cubic-bezier(.25, .8, .25, 1);
            border-color: $theme-white;
          }
        }

        .container {
            width: 16px;
            height: 16px;
            position: relative;
            border-radius: 2px;
            border: 2px solid $grey-3;
            transition: .4s cubic-bezier(.25, .8, .25, 1);
            display: inline-block;
            vertical-align: middle;

            &.indeterminate {
                background-color: $grey-5;
                border-color: $grey-5;

                &:after {
                    opacity: 1;
                    width: 8px;
                    height: 0px;
                    top: 5px;
                    left: 2px;
                    transform: rotate(0) scale3D(1, 1, 1);
                    transition: .4s cubic-bezier(.25, .8, .25, 1);
                    border-color: $theme-white;
                }
            }

            &:hover {
                border-color: $grey-5;
            }

            input {
                position: absolute;
                left: -999em;
            }

            &:after {
                width: 6px;
                height: 10px;
                top: 0;
                left: 3px;
                border: 2px solid transparent;
                border-top: 0;
                border-left: 0;
                opacity: 0;
                transform: rotate(45deg) scale3D(.15, .15, 1);
                position: absolute;
                transition: .4s cubic-bezier(.55, 0, .55, .2);
                content: ' ';
            }
        }

        .label {
            margin-left: 8px;
            cursor: pointer;
            vertical-align: middle;

            &:hover {
                text-shadow: 1px 1px rgba(0, 0, 0, 0.2)
            }
        }
    }
</style>
