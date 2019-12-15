<template>
  <v-dialog v-model="visible" max-width="500">
    <v-card>

      <v-card-text v-html="params.text"></v-card-text>

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

export default {
    name: 'xSafeguard',
    components: { XButton },
    data() {
        return {
            visible: false,
            params: {}
        }
    },
    methods: {
        onConfirm() {
            if (this.params.onConfirm) {
                this.params.onConfirm()
            }
            this.visible = false
        },
        onCancel() {
            if (this.params.onCancel) {
                this.params.onCancel()
            }
            this.visible = false
        },
        show({ text="Are you sure?", onConfirm, onCancel, confirmText="Confirm", cancelText="Cancel"}) {
            this.visible = true
            this.params = { text, onConfirm, onCancel, confirmText, cancelText }
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
    }
    .v-card__text {
        padding-top: 24px !important;
    }
    .v-overlay--active {
        z-index: 1001 !important;
    }

    #safeguard-save-btn, #safeguard-cancel-btn {
        width: auto;
    }
</style>