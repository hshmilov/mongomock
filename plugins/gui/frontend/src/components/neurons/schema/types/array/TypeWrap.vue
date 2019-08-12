<template>
  <div
    class="object"
    :class="{ expand }"
  >
    <label
      v-if="label"
      :title="description"
      class="label"
      :for="name"
    >{{ label }}<div
      v-if="!required"
      class="hint"
    >optional</div>
    </label>
    <slot />
  </div>
</template>

<script>
  export default {
    name: 'XTypeWrap',
    props: {
      name: {
        type: [String, Number],
        default: ''
      },
      type: {
        type: String,
        default: ''
      },
      description: {
        type: String,
        default: ''
      },
      title: {
        type: String,
        default: ''
      },
      required: {
        type: [Boolean, Array],
        default: true
      },
      items: {
        type: [Array, Object],
        default: () => []
      },
      path: {
        type: Array,
        default: () => []
      },
      expand: {
        type: Boolean,
        default: true
      }
    },
    computed: {
      label () {
        if (this.type === 'array') { return '' }
        return this.title
      }
    }
  }
</script>

<style lang="scss">
    .object {
        display: inline-block;
        width: auto;
        &.expand {
            width: 100%;
        }
    }
</style>