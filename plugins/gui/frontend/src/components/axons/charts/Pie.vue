<template>
  <div
    class="x-pie"
    :class="{disabled: readOnly}"
  >
    <svg
      viewBox="-1 -1 2 2"
      @mouseout="inHover = -1"
    >
      <defs>
        <linearGradient id="intersection-1-2">
          <stop
            class="extra-stop-1"
            offset="0%"
          />
          <template v-for="n in 9">
            <stop
              :class="`extra-stop-${!(n % 2) ? 3 : 1}`"
              :offset="`${n}0%`"
            />
            <stop
              :class="`extra-stop-${!(n % 2) ? 1 : 3}`"
              :offset="`${n}0%`"
            />
          </template>
          <stop
            class="extra-stop-3"
            offset="100%"
          />
        </linearGradient>
      </defs>
      <g
        v-for="(slice, index) in slices"
        :key="index"
        :class="`slice-${index}`"
        @click="onClick(index)"
        @mouseover="onHover($event, index)"
      >
        <path
          :d="slice.path"
          :class="`filling ${slice.class} ${inHover === index? 'in-hover' : ''}`"
        />
        <text
          v-if="showPercentageText(slice.value)"
          class="scaling"
          text-anchor="middle"
          :x="slice.middle.x"
          :y="slice.middle.y"
        >{{ Math.round(slice.value * 100) }}%
        </text>
      </g>
    </svg>
    <div
      v-show="hoverDetails.title"
      ref="tooltip"
      class="tooltip"
    >
      <div class="tooltip-title">{{ hoverDetails.parentTitle }}</div>
      <div class="tooltip-content">
        <div class="tooltip-legend">
          <div
            class="legend"
            :class="hoverDetails.class"
          />
          {{ hoverDetails.title }}
        </div>
        <div>{{ hoverDetails.percentage }}%</div>
      </div>
      <div
        v-for="component in hoverDetails.components"
        class="tooltip-content"
      >
        <div class="tooltip-legend">
          <div
            class="legend round"
            :class="component.class"
          />
          {{ component.name }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  export default {
    name: 'XPie',
    props: {
      data: {
        type: Array,
        required: true
      },
      forceText: {
        type: Boolean,
        default: false
      },
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        inHover: -1
      }
    },
    computed: {
      processedData () {
        return this.data.map((item, index) => {
          if (item.remainder) {
            return { class: 'theme-fill-gray-light', ...item }
          } else if (item.intersection) {
            return { class: `fill-intersection-${index - 1}-${index}`, ...item }
          }
          if (this.data.length === 2) {
            return { class: `indicator-fill-${Math.ceil(item.value * 4)}`, ...item }
          }
          return { class: `extra-fill-${(index % 6) || 6}`, ...item }
        })
      },
      slices () {
        let cumulativePortion = 0
        return this.processedData.map((slice) => {
          // Starting slice at the end of previous one, and ending after percentage defined for item
          const [startX, startY] = this.getCoordinatesForPercent(cumulativePortion)
          cumulativePortion += slice.value / 2
          const [middleX, middleY] = this.getCoordinatesForPercent(cumulativePortion)
          cumulativePortion += slice.value / 2
          const [endX, endY] = this.getCoordinatesForPercent(cumulativePortion)
          return {
            ...slice,
            path: [
              `M ${startX} ${startY}`, // Move
              `A 1 1 0 ${slice.value > 0.5? 1 : 0} 1 ${endX} ${endY}`, // Arc
              `L 0 0` // Line
            ].join(' '),
            middle: { x: middleX * 0.7, y: middleY * (middleY > 0 ? 0.8 : 0.5) }
          }
        })
      },
      hoverDetails () {
        if (!this.data || this.data.length === 0) return {}
        if (this.inHover === -1) return {}
        let percentage = Math.round(this.processedData[this.inHover].value * 100)
        if (percentage < 0) {
          percentage = 100 + percentage
        }
        let title = this.processedData[this.inHover].name
        let components = []
        if (this.processedData[this.inHover].intersection) {
          title = 'Intersection'
          components.push({ ...this.processedData[this.inHover - 1] })
          components.push({ ...this.processedData[this.inHover + 1] })
        }
        if (this.inHover === 0) {
          title = 'Excluding'
          components = this.processedData.filter(data => !data.intersection && !data.remainder)
        }
        return {
          parentTitle: this.data[0].name, title, percentage, class: this.processedData[this.inHover].class,
          components
        }
      }
    },
    methods: {
      getCoordinatesForPercent (portion) {
        return [Math.cos(2 * Math.PI * portion), Math.sin(2 * Math.PI * portion)]
      },
      onHover (event, index) {
        this.inHover = index
        if (!this.$refs || !this.$refs.tooltip) return
        this.$refs.tooltip.style.top = event.clientY + 10 + 'px'
        this.$refs.tooltip.style.left = event.clientX + 10 + 'px'
      },
      showPercentageText (val) {
        return (this.forceText && val > 0) || val > 0.04
      },
      onClick (index) {
        if (this.readOnly) return
        this.$emit('click-one', index)
      }
    }
  }
</script>

<style lang="scss">
    .x-pie {
        margin: auto;
        width: 240px;

        .fill-intersection-1-2 {
            fill: url(#intersection-1-2);
            background: repeating-linear-gradient(45deg, nth($extra-colours, 1), nth($extra-colours, 1) 4px,
                    nth($extra-colours, 2) 4px, nth($extra-colours, 2) 8px);
        }

        g {
            cursor: pointer;

            path {
                opacity: 0.8;
                transition: opacity ease-in 0.4s;

                &.in-hover {
                    opacity: 1;
                }
            }

            text {
                font-size: 1%;
                fill: $theme-black;
            }
        }

        &.disabled g {
            cursor: default;
        }
    }

    .tooltip {
        .tooltip-content {
            .tooltip-legend {
                margin-right: 12px;
                flex: 1 0 auto;
                max-width: 200px;

                .legend {
                    display: inline-block;
                    height: 16px;
                    width: 16px;
                    border-radius: 4px;
                    margin-right: 4px;
                    vertical-align: middle;

                    &.round {
                        border-radius: 100%;
                        width: 8px;
                        height: 8px;
                    }
                }
            }
        }

    }
</style>
