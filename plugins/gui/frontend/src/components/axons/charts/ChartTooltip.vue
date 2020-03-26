<template>
  <div class="x-chart-tooltip">
    <XTooltip
      v-show="isVisible"
      ref="tooltip"
    >
      <template slot="header">
        <div
          class="header-content"
          :class="header.class"
        >
          <div class="name">
            {{ header.name }}
          </div>
          <div>
            <span class="value">{{ header.value }}</span>
            <span class="percentage">{{ header.percentage }}</span>
          </div>
        </div>
      </template>
      <template slot="body">
        <div class="body-content">
          <span class="value">{{ body.value }}</span>
          <span class="percentage">{{ body.percentage }}</span>
        </div>
        <div
          v-for="item in additionalData"
          :key="item.name"
          class="body-content"
        >
          <div class="body-component-name">
            {{ item.name }}
          </div>
        </div>
      </template>
    </XTooltip>
    <div
      class="wrapper"
      @mouseover="showTooltip"
      @mouseleave="show = false"
    >
      <slot name="tooltipActivator" />
    </div>
  </div>
</template>

<script>
import _isEmpty from 'lodash/isEmpty';
import XTooltip from '../popover/Tooltip.vue';

export default {
  name: 'XChartTooltip',
  components: { XTooltip },
  props: {
    header: {
      type: Object,
      default: () => ({}),
    },
    body: {
      type: Object,
      default: () => ({}),
    },
    additionalData: {
      type: Array,
      default: () => ([]),
    },
  },
  data() {
    return {
      show: false,
    };
  },
  computed: {
    isVisible() {
      const tooltipData = { ...this.header, ...this.body, ...this.additionalData };
      return this.show && !_isEmpty(tooltipData);
    },
  },
  methods: {
    showTooltip(e) {
      this.$refs.tooltip.$el.style.top = `${e.clientY + 10}px`;
      this.$refs.tooltip.$el.style.left = `${e.clientX + 10}px`;
      this.show = true;
    },
  },
};

</script>

<style lang="scss">
  .x-chart-tooltip {
    flex-grow: 1;
    display: flex;

    .wrapper {
      flex-grow: 1;
    }

    .x-tooltip {
      min-width: 20ch;
      position: fixed;
      padding: 0;

      .percentage {
        font-size: small;
      }

      .name, .value {
        max-width: 40ch;
        text-overflow: ellipsis;
        overflow: hidden;
      }

      .header-content {
        color: $theme-white;
        display: flex;
        justify-content: space-between;
        padding: 0 8px;
        opacity: 0.8;

        &.pie-fill-1 {
          color: $theme-black;
        }

        .name {
          margin-right: 8px;
        }
      }

      .body-content {
        padding: 0 8px;
        display: flex;
        justify-content: space-between;

        .percentage {
          opacity: 0.5;
        }
      }
    }
  }
</style>
