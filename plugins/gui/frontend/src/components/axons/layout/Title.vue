<template>
  <div
    class="x-title"
    :class="{disabled}"
  >
    <img
      :src="require(`Logos/${logo}.png`)"
      :height="height"
      class="md-image"
    >
    <div class="text"><slot /></div>
    <slot name="actions" />
  </div>
</template>

<script>
  export default {
    name: 'XTitle',
    props: {
      logo: {
        type: String,
        required: true
      },
      disabled: {
        type: Boolean,
        default: false
      },
      height: {
        type: Number,
        default: 24
      }
    }
  }
</script>

<style lang="scss">
    .x-title {
        display: flex;
        align-items: center;

        .text {
            margin-left: 12px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        &.disabled {
            .md-image {
                opacity: 0.6;
            }

            .text {
                color: $grey-3;
            }
        }
    }
</style>