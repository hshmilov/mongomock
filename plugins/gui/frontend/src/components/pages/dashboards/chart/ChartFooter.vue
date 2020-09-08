<template>
  <footer class="x-chart__footer">
    <!-- <ADivider /> -->
    <p
      v-if="displayCount && !showLess"
      :class="['footer__total', {'footer__total--w-pagination': pagination}]"
    >
      <span>{{ countLabel }}</span>
    </p>
    <div
      v-if="pagination && !showLess"
      class="footer__pagination"
    >
      <APagination
        size="small"
        :show-total="totalResults"
        :current="page"
        :total="count"
        :page-size="limit"
        :default-current="1"
        @change="$event => $emit('on-page-changed', $event)"
      />
    </div>
    <div
      v-if="trend || legend || draggable"
      :class="['footer__bottom', { 'footer__bottom--w-pagination': pagination && !showLess}]"
    >
      <div
        v-if="!showLess"
        class="footer__bottom__actions"
      >
        <XButton
          v-if="legend && !expanded"
          title="Chart legend"
          class="legend"
          type="link"
          @click="$emit('open-drawer', 'legend')"
        >
          <XIcon
            family="action"
            type="legendOpen"
          />
        </XButton>
        <XButton
          v-if="trend && !expanded"
          class="trend"
          type="link"
          :title="Boolean(trendDisabled) ? trendDisabled : 'Timeline'"
          :disabled="Boolean(trendDisabled)"
          @click="$emit('open-drawer', 'trend')"
        >
          <XIcon
            type="line-chart"
          />
        </XButton>
        <XButton
          v-if="expanded"
          class="close-drawer"
          type="link"
          @click="$emit('close-drawer')"
        >
          <XIcon
            type="close-circle"
          />
        </XButton>
      </div>
      <XIcon
        v-if="draggable"
        class="drag-handle"
        family="action"
        type="drag"
      />
    </div>
  </footer>
</template>

<script>
import { Pagination } from 'ant-design-vue';
import XIcon from '@axons/icons/Icon';
import XButton from '@axons/inputs/Button.vue';
import { getTotalResultsTitle } from '@/helpers/dashboard';

export default {
  name: 'XChartFooter',
  components: {
    APagination: Pagination,
    XIcon,
    XButton,
  },
  props: {
    // pagination props
    pagination: {
      type: Boolean,
      default: false,
    },
    page: {
      type: Number,
      default: 1,
    },
    limit: {
      type: Number,
      default: 5,
    },
    chartData: {
      type: Object,
      required: true,
    },
    // display count
    displayCount: {
      type: Boolean,
      default: false,
    },
    totalItemsName: {
      type: String,
      default: 'items',
    },
    // chart bottom footer props
    draggable: {
      type: Boolean,
      default: false,
    },
    legend: {
      type: Boolean,
      default: false,
    },
    expanded: {
      type: Boolean,
      default: false,
    },
    formatCountLabel: {
      type: Function,
      default: undefined,
    },
    trend: {
      type: Boolean,
      default: false,
    },
    trendDisabled: {
      type: String,
      default: '',
    },
    // true when chart's data empty or when error raised
    showLess: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    count() {
      return this.chartData.count;
    },
    countLabel() {
      if (this.formatCountLabel) {
        return this.formatCountLabel`${this.chartData}`;
      }
      return `Total ${this.count}`;
    },
  },
  methods: {
    totalResults(total, range) {
      return getTotalResultsTitle(total, range, this.totalItemsName);
    },
  },
};
</script>

<style lang="scss">
.x-chart__footer {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: center;
    height: auto;

  .ant-divider.ant-divider-horizontal {
    margin: 4px 0;
    background-color: $theme-orange;
  }
  .footer__total {
    padding: 4px 0;
    font-weight: bold;
    margin: 4px;
    &--w-pagination {
      margin: 4px 4px 16px 4px;
    }
  }
  .footer__pagination {
    width: 100%;
    text-align: center;

    .ant-pagination-total-text {
      display: block;
      margin-bottom: 8px;
      position: absolute;
      top: 45px;
      width: 100%;
    }
    .ant-pagination-item a {
      margin: 0 4px;
      // delete after vuetify will be removed from project (link style override)
      color: rgba(0, 0, 0, 0.65);
      text-decoration: none;
      transition: none;
    }
    .ant-pagination.mini {
      position: relative;
      .ant-pagination-prev, .ant-pagination-next {
        min-width: 10px;
      }
    }
  }
  .footer__bottom {
    width: 100%;
    height: 30px;
    position: relative;
    bottom: 0px;
    display: flex;
    flex-direction: row;
    align-items: flex-end;

    &--w-pagination {
      margin-top: 40px;
    }

    &__actions {
      .x-button {
        padding: 0 4px;
        font-size: 16px;
      }
    }

    .drag-handle {
      font-size: 24px;
      color: $grey-3;
      position: absolute;
      right: calc((100% / 2) + -12px);
      cursor: move;
      &:hover {
        color: $grey-5;
      }
    }
  }
}
</style>
