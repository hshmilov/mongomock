<template>
  <defs>
    <linearGradient
      :id="intersectingColors.length ? `defined-colors-${chartId}` : 'intersection-2-3'"
    >
      <stop
        class="pie-stop-2"
        :style="firstIntersectionStyle"
        offset="0%"
      />
      <template v-for="n in 9">
        <stop
          :key="`pie-stop-${n}`"
          :class="`pie-stop-${(n % 2) ? 2 : 3}`"
          :style="(n % 2) ? secondIntersectionStyle : firstIntersectionStyle"
          :offset="`${n}0%`"
        />
      </template>
      <stop
        class="pie-stop-2"
        :style="firstIntersectionStyle"
        offset="100%"
      />
    </linearGradient>
  </defs>
</template>

<script>
export default {
  name: 'IntersectionSlice',
  props: {
    chartId: {
      type: String,
      default: '',
    },
    intersectingColors: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    firstIntersectionStyle() {
      const [firstIntersectionColor] = this.intersectingColors;
      return firstIntersectionColor ? { 'stop-color': firstIntersectionColor } : {};
    },
    secondIntersectionStyle() {
      const [_, secondIntersectionColor] = this.intersectingColors;
      return secondIntersectionColor ? { 'stop-color': secondIntersectionColor } : {};
    },
  },
};
</script>

<style lang="scss" scoped></style>
