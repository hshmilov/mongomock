<template>
  <header class="x-chart__header">
    <div class="x-chart__header__title">
      <h3
        class="chart-title"
        :title="title"
      >
        {{ title }}
      </h3>
      <span v-if="filters.history">
        {{ historicalDate }}
      </span>
    </div>
    <ATooltip
      :mouse-enter-delay="0.5"
      :mouse-leave-delay="0"
      placement="bottom"
    >
      <template slot="title">
        {{ filterLayerVisible ? 'Back' : 'Chart filters' }}
      </template>
      <XButton
        v-if="filterable"
        type="link"
        class="x-chart__header__filter-icon"
        @click="$emit('on-open-filters')"
      >
        <XIcon
          class="header__filter-icon"
          :class="{ 'header__filter-icon--active': !filterLayerVisible && filterActive }"
          :type="filterLayerVisible ? 'rollback' : 'filter'"
        />
      </XButton>
    </ATooltip>
    <slot name="actions-menu" />
  </header>
</template>

<script>
import { Tooltip as ATooltip } from 'ant-design-vue';
import dayjs from 'dayjs';
import { mapGetters } from 'vuex';
import { DATE_FORMAT } from '@store/getters';

export default {
  name: 'XChartHeader',
  components: { ATooltip },
  props: {
    filters: {
      type: Object,
      required: true,
    },
    filterable: {
      type: Boolean,
      default: false,
    },
    filterLayerVisible: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: '',
    },
  },
  computed: {
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    filterActive() {
      return Boolean(this.filters.search || this.filters.history);
    },
    historicalDate() {
      return dayjs(this.filters.history).format(this.dateFormat);
    },
  },
};
</script>

<style lang="scss">
.x-chart__header {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: flex-start;

  &__title {
    display: flex;
    flex-direction: column;
    width: 81%;
    h3 {
      margin: 0;
      text-overflow: ellipsis;
      white-space: nowrap;
      overflow: hidden;
      font-size: 16px;
      font-weight: 400;
      line-height: 16px;
    }
  }

  &__filter-icon {
    position: relative;
    bottom: 6px;
    font-size: 16px;
  }

  .header__filter-icon--active:after {
    content: '';
    position: absolute;
    border-radius: 50%;
    width: 8px;
    height: 8px;
    /* transform: rotate(45deg); */
    background-color: $theme-orange;
    right: 10px;
    top: 4px;
  }
}
</style>
