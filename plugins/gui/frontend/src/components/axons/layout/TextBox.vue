<template>
  <div
    class="x-text-box"
    :class="{disabled: !clickable, selected, capitalized}"
  >
    <slot name="logo" />
    <div class="content">
      {{ text }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'XTextBox',
  props: {
    text: {
      type: String,
      default: '',
    },
    selected: Boolean,
    clickable: {
      type: Boolean,
      default: true,
    },
    capitalized: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style lang="scss">
    .x-text-box {
        background-color: $grey-1;
        display: flex;
        align-items: center;
        position: relative;
        border-radius: 24px;
        min-width: 240px;
        max-width: 50ch;
        height: 48px;
        &.capitalized {
          text-transform: capitalize;
        }
        &:not(.disabled) {
            cursor: pointer;
        }
        &:hover:not(.disabled), &.selected {
            background-color: $grey-2;
        }
        .content {
            padding-left: 12px;
            padding-right: 12px;
            text-overflow: ellipsis;
            white-space: nowrap;
            width: calc(100% - 24px);
            overflow-x: hidden;
        }
    }
</style>
