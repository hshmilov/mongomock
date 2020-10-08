<template>
  <VDialog
    v-model="visible"
    max-width="500"
    @keydown.enter="onConfirm"
    @keydown.esc="onCancel"
  >
    <VCard>
      <VCardText v-html="params.text" />
      <XChexkbox
        v-if="params.showCheckbox"
        v-model="customComponentValue"
        :label="params.checkboxLabel"
      />
      <VCardActions>
        <VSpacer />

        <XButton
          id="safeguard-cancel-btn"
          type="link"
          @click="onCancel"
        >
          {{ params.cancelText }}
        </XButton>
        <XButton
          id="safeguard-save-btn"
          type="primary"
          @click="onConfirm"
        >
          {{ params.confirmText }}
        </XButton>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<script>
import XChexkbox from '@axons/inputs/Checkbox.vue';
import Plugin from './index';

export default {
  name: 'XSafeguard',
  components: { XChexkbox },
  data() {
    return {
      visible: false,
      params: {},
      customComponentValue: undefined,
    };
  },
  beforeMount() {
    Plugin.EventBus.$on('show', (params) => {
      this.show(params);
    });
  },
  methods: {
    onConfirm() {
      if (this.params.onConfirm) {
        this.params.onConfirm(this.customComponentValue);
      }
      this.visible = false;
    },
    onCancel() {
      if (this.params.onCancel) {
        this.params.onCancel();
      }
      this.visible = false;
    },
    show({
      text = 'Are you sure?', onConfirm, onCancel, confirmText = 'Confirm', cancelText = 'Cancel', checkbox,
    }) {
      this.visible = true;
      this.params = {
        text, onConfirm, onCancel, confirmText, cancelText,
      };
      if (checkbox) {
        this.params.showCheckbox = !!checkbox;
        this.params.checkboxLabel = checkbox.label;
        this.customComponentValue = checkbox.initialValue;
      }
    },
  },
};
</script>

<style lang="scss">
    .v-dialog__content--active {
        z-index: 1004 !important;

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
    .v-application > .v-overlay--active {
        z-index: 1003 !important;
    }

    #safeguard-save-btn, #safeguard-cancel-btn {
        width: auto;
    }
</style>
