<template>
  <span class="x-safeguard-button">
    <x-button
      :id="id"
      v-bind="propsToPass"
      @click="onClick"
    ><slot name="button-text" />
    </x-button>
    <x-modal
      v-if="open"
      :approve-text="approveText"
      :dismiss-text="dismissText"
      :size="modalSize"
      @close="onCancel"
      @confirm="onConfirm"
    >
      <div
        v-if="this.$slots.message"
        slot="body"
      >
        <slot
          name="message"
        />
      </div>
    </x-modal>
  </span>
</template>

<script>
    import xButton from '../../axons/inputs/Button.vue'
    import xModal from '../../axons/popover/Modal.vue'

    const originalProps = {...xButton.props}

    export default {
        name: 'XSafeguardButton',
        components: {
            xButton, xModal
        },
        props: {
            ...originalProps,
            approveText: {
                type: String,
                default: 'Ok'
            },
            dismissText: {
                type: String,
                default: 'Cancel'
            },
            modalSize: {
                type: String,
                default: 'lg'
            },
            id: {
              type: String,
              default: null
            }
        },
        data() {
            return {
                open: false
            }
        },
        computed: {
          propsToPass() {
            return Object.keys(originalProps).reduce( (acc, curr, next) => {
              acc[curr] = this.$props[curr]
              return acc
            },{})
          }
        },
        methods: {
            onClick (e) {
                this.open = true
            },
            onCancel() {
                this.open = false
            },
            onConfirm(e) {
                this.open = false
                this.$emit('click', e)
            }
        }
    }
</script>

<style lang="scss">
    .x-safeguard-button {
        .modal-footer {
            display: flex;
            justify-content: flex-end;

            .x-button {
                width: auto;
            }
        }
    }
</style>