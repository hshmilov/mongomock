<template>
  <Transition
    name="modal"
    @after-enter="$emit('enter')"
    @after-leave="$emit('leave')"
  >
    <div class="x-modal">
      <div :class="`modal-container w-${size}`">
        <div
          v-if="title"
          class="modal-header"
        >
          <div class="modal-header-title">
            {{ title }}
          </div>
          <XButton
            v-if="dismissable"
            type="link"
            @click="$emit('close')"
          >
            x
          </XButton>
        </div>
        <div class="modal-body">
          <slot
            name="body"
            @submit="$emit('confirm')"
          >
            Are you sure?
          </slot>
        </div>
        <div class="modal-footer">
          <slot name="footer">
            <XButton
              type="link"
              @click.prevent.stop="$emit('close')"
            >
              {{ dismissText }}
            </XButton>
            <XButton
              type="primary"
              :id="approveId"
              :disabled="disabled"
              @click.prevent.stop="onApprove"
            >
              {{ approveText }}
            </XButton>
          </slot>
        </div>
      </div>
      <div
        class="modal-overlay"
        @click.prevent.stop="$emit('close')"
        @keyup.esc="$emit('close')"
      />
    </div>
  </Transition>
</template>

<script>
import XButton from '../../inputs/Button.vue';

export default {
  name: 'XModal',
  components: { XButton },
  props: {
    approveText: { default: 'OK' },
    approveId: {},
    dismissText: { default: 'Cancel' },
    disabled: { default: false },
    size: { default: 'xl' },
    title: {},
    dismissable: { default: false },
  },
  mounted() {
    if (this.$el.querySelector('input')) {
      this.$el.querySelector('input').focus();
    }
  },
  methods: {
    onApprove() {
      this.$emit('confirm');
      return false;
    },
  },
};
</script>

<style lang="scss">
    .x-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1001;
        display: grid;

        .modal-container {
            position: relative;
            margin: auto;
            background-color: $theme-white;
            border-radius: 2px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, .33);
            z-index: 1001;

            .modal-header {
                display: flex;
                border-bottom: 1px solid $grey-2;
                padding: 12px 24px 12px 24px;
                .modal-header-title {
                    flex: 1 0 auto;
                    font-weight: 500;
                    font-size: 16px;
                }
            }
            .modal-body {
                padding: 24px;
                padding-bottom: 0;
                margin-bottom: 24px;
                max-height: 650px;
                overflow-y: auto;

                .form-group:last-of-type {
                    margin-bottom: 0;
                }
            }

            .modal-footer {
              padding: 24px;
              padding-top: 0;
              border: 0;
              text-align: right;
            }
        }

        .modal-overlay {
            position: fixed;
            z-index: 1000;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, .5);
            transition: opacity .3s ease;
        }
    }

    .modal-enter {
        opacity: 0;
    }

    .modal-leave-active {
        opacity: 0;
    }

    .modal-enter .modal-container,
    .modal-leave-active .modal-container {
        transform: scale(1.1);
    }
</style>
