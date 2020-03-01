<template>
  <VDialog
    v-model="visible"
    max-width="500"
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
          link
          @click="onCancel"
        >
          {{ params.cancelText }}
        </XButton>
        <XButton
          id="safeguard-save-btn"
          @click="onConfirm"
        >
          {{ params.confirmText }}
        </XButton>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<script>
import Plugin from './index';
import XButton from '../../components/axons/inputs/Button.vue';
import XChexkbox from '../../components/axons/inputs/Checkbox.vue';

export default {
  name: 'XSafeguard',
  components: { XButton, XChexkbox },
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
