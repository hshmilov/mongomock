<template>
  <div
    class="main__body"
    :class="classNames"
  >
    <!-- Chart's data being fethced -->
    <div
      v-if="loading"
      class="main__body--loading"
    >
      <ASpin size="large" />
    </div>
    <!-- Chart has error -->
    <div
      v-else-if="error"
      class="main__body--error"
    >
      <XIcon
        type="warning"
      />
      Something went wrong
      <XButton
        type="primary"
        :style="{width: '200px'}"
        @click="$emit('refresh')"
      >
        Try Again
      </XButton>
    </div>
    <!-- Chart has no data -->
    <div
      v-else-if="empty"
      class="main__body--empty"
    >
      <XIcon
        family="illustration"
        type="binocular"
        :style="{fontSize: '100px'}"
      />
      <p>No data found</p>
    </div>
    <!-- slot for data vizualiztion -->
    <slot v-else />
  </div>
</template>

<script>
import { Spin as ASpin } from 'ant-design-vue';

export default {
  name: 'XChartContent',
  components: { ASpin },
  props: {
    loading: {
      type: Boolean,
      default: true,
    },
    error: {
      type: Boolean,
      default: false,
    },
    empty: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    classNames() {
      return {
        'main__body--error': this.error,
        'main__body--loading': this.loading,
        'main__body--empty': this.empty,
      };
    },
  },
};
</script>
