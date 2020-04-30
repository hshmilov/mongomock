<template>
  <VDialog
    v-model="visible"
    max-width="500"
  >
    <VCard>
      <VCardText v-html="params.text" />
      <VCardActions>
        <VSpacer />
        <XButton
          id="message-confirm-btn"
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
import Plugin from './index';
import XButton from '../../components/axons/inputs/Button.vue';

export default {
  name: 'XMessageModal',
  components: { XButton },
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
    show({
      text = 'Are you sure?', onConfirm, confirmText = 'Confirm', cancelText = 'Cancel',
    }) {
      this.visible = true;
      this.params = {
        text, onConfirm, confirmText, cancelText,
      };
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

    #message-confirm-btn {
        width: auto;
    }
</style>
