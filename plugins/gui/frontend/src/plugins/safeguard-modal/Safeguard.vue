<template>
  <v-dialog v-model="visible" max-width="500">
    <v-card>

      <v-card-text v-html="params.text"></v-card-text>
      <x-chexkbox v-if="params.showCheckbox" v-model="customComponentValue" :label="params.checkboxLabel"/>
      <v-card-actions>
        <v-spacer></v-spacer>

        <x-button id="safeguard-cancel-btn" link @click="onCancel">{{params.cancelText}}</x-button>
        <x-button id="safeguard-save-btn" @click="onConfirm">{{params.confirmText}}</x-button>

      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import Plugin from './index'
import XButton from '../../components/axons/inputs/Button.vue'
import XChexkbox from '../../components/axons/inputs/Checkbox.vue'

export default {
    name: 'xSafeguard',
    components: { XButton, XChexkbox},
    data() {
        return {
            visible: false,
            params: {},
            customComponentValue: undefined
        }
    },
    methods: {
        onConfirm() {
            if (this.params.onConfirm) {
                this.params.onConfirm(this.customComponentValue)
            }
            this.visible = false
        },
        onCancel() {
            if (this.params.onCancel) {
                this.params.onCancel()
            }
            this.visible = false
        },
        show({ text="Are you sure?", onConfirm, onCancel, confirmText="Confirm", cancelText="Cancel", checkbox }) {
            this.visible = true
            this.params = { text, onConfirm, onCancel, confirmText, cancelText }
            if (checkbox) {
                this.params['showCheckbox'] = !!checkbox
                this.params['checkboxLabel'] = checkbox.label
                this.customComponentValue = checkbox.initialValue
            }
        }
    },
    beforeMount() {
        Plugin.EventBus.$on('show', (params) => {
            this.show(params)
        })
    }
}
</script>

<style lang="scss">
    .v-dialog__content--active {
        z-index: 1002 !important;
        
        .x-checkbox {
            padding: 0 24px;
        }
    }
    .v-card__text {
        padding-top: 24px !important;
    }
    .theme--light.v-card > .v-card__text {
      color: unset !important;
    }
    .v-overlay--active {
        z-index: 1001 !important;
    }

    #safeguard-save-btn, #safeguard-cancel-btn {
        width: auto;
    }
</style>