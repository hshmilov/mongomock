<template>
  <div
    v-show="isActive"
    :class="{'active': isActive, [ id ]: true}"
    class="x-tab"
    role="tabpanel"
  >
    <slot />
  </div>
</template>

<script>
  export default {
    name: 'XTab',
    props: {
      id: {
        type: String,
        required: true
      },
      title: {
        type: String,
        required: true
      },
      selected: {
        type: Boolean,
        default: false
      },
      logo: {
        type: String,
        default: ''
      },
      disabled: {
        type: Boolean,
        default: false
      },
      editable: {
        type: Boolean,
        default: false
      },
      removable: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        isActive: false
      }
    },
    created () {
      this.isActive = this.selected
    }
  }
</script>

<style lang="scss">
    .x-tab {
        height: 100%;
    }

</style>