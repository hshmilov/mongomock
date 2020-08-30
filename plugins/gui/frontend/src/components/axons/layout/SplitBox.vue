<template>
  <XBox class="x-split-box">
    <div class="main">
      <slot name="main" />
    </div>
    <div class="details">
      <slot name="details" />
    </div>
  </XBox>
</template>

<script>
import XBox from './Box.vue';

export default {
  name: 'XSplitBox',
  components: {
    XBox,
  },
};
</script>

<style lang="scss">
    .x-split-box {
        height: 100%;
        display: flex;
        overflow: hidden;
        > .main {
            height: 100%;
            width: 600px;
            padding: 12px;
            margin-right: 12px;
        }
        .details {
            height: 100%;
            width: calc(100% - 600px);
        }
    }
</style>
