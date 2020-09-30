<template>
  <div class="x-paginator">
    <XButton
      v-if="count > limit"
      type="link"
      class="first"
      :disabled="isBackDisabled"
      @click="onClickPage(1)"
      @keyup.enter="onClickPage(1)"
    >
      &lt;&lt;
    </XButton>
    <XButton
      v-if="count > limit"
      type="link"
      class="previous"
      :disabled="isBackDisabled"
      @click="onClickPage(page-1)"
      @keyup.enter="onClickPage(page-1)"
    >
      &lt;
    </XButton>
    <div class="paginator-text">
      <template v-if="showTop && page === 1">
        Top <strong class="num-of-items"> {{ to }}</strong>
      </template>
      <template v-else>
        <strong class="from-item"> {{ from }} </strong>
        - <strong class="to-item"> {{ to }}</strong>
      </template>
      of <strong class="total-num-of-items"> {{ count }}</strong>
    </div>
    <XButton
      v-if="count > limit"
      type="link"
      class="next"
      :disabled="isNextDisabled"
      @click="onClickPage(page+1)"
      @keyup.enter="onClickPage(page+1)"
    >
      &gt;
    </XButton>
    <XButton
      v-if="count > limit"
      type="link"
      class="last"
      :disabled="isNextDisabled"
      @click="onClickPage(pageCount)"
      @keyup.enter="onClickPage(pageCount)"
    >
      &gt;&gt;
    </XButton>
  </div>
</template>
<script>

export default {
  name: 'XPaginator',
  props: {
    limit: {
      type: Number,
      default: 5,
    },
    from: {
      type: Number,
      required: true,
    },
    to: {
      type: Number,
      required: true,
    },
    count: {
      type: Number,
      required: true,
    },
    showTop: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      page: 1,
    };
  },
  computed: {
    pageTo() {
      if (this.limit <= this.count) {
        return Math.min(this.page * this.limit, this.count);
      }
      return this.count;
    },
    pageFrom() {
      if (this.count % this.limit !== 0 && this.page === this.pageCount) {
        return this.count - (this.count % this.limit) + 1;
      }
      return this.pageTo - this.limit + 1;
    },
    pageCount() {
      return this.count % this.limit === 0
        ? this.count / this.limit
        : Math.floor(this.count / this.limit) + 1;
    },
    isNextDisabled() {
      return !(this.page + 1 <= this.pageCount && this.to < this.count);
    },
    isBackDisabled() {
      return !(this.page - 1 >= 1);
    },
  },
  watch: {
    count() {
      this.page = 1;
      this.emitRange();
    },
  },
  mounted() {
    this.onClickPage(1);
  },
  methods: {
    onClickPage(page) {
      this.$emit('change');
      this.page = page;
      this.emitRange();
    },
    emitRange() {
      this.$emit('update:from', this.pageFrom);
      this.$emit('update:to', this.pageTo);
    },
  },
};
</script>
<style lang="scss">
  .x-paginator {
    display: flex;
    width: 100%;
    min-height: 28px;
    align-items: center;
    justify-content: center;
    background: $theme-white;
    border-bottom: 2px solid $theme-white;
    border-radius: 2px;

    .paginator-text {
      line-height: 30px;
    }

    .x-button {
      width: 12px;
      background: transparent;
      display: flex;
      justify-content: center;
      line-height: 30px;
      &:not(:disabled) {
        color: $theme-black;
        &:hover {
          text-shadow: $text-shadow;
        }
      }
    }
    .active:hover {
      cursor: default;
    }

  }


</style>
