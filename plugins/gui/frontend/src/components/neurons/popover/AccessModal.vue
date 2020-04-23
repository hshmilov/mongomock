<template>
  <XModal
    v-if="value"
    @close="dismissAccessMessage"
  >
    <div slot="body">
      You do not have permission to access the {{ value }} screen
    </div>
    <div slot="footer">
      <XButton
        type="primary"
        @click="dismissAccessMessage"
      >
        OK
      </XButton>
    </div>
  </XModal>
</template>

<script>
import XButton from '../../axons/inputs/Button.vue';
import XModal from '../../axons/popover/Modal/index.vue';

export default {
  name: 'XAccessModal',
  components: { XButton, XModal },
  props: { value: {} },
  methods: {
    dismissAccessMessage() {
      this.$emit('input', '');
    },
  },
};
</script>

<style lang="scss">

</style>
