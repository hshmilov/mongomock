<template>
  <svg :height="radius * 2" :width="radius * 2">
    <circle
      v-if="background"
      stroke="#f5f5f5"
      fill="transparent"
      :stroke-width="stroke"
      :r="normalizedRadius"
      :cx="radius"
      :cy="radius"
    />
    <circle
      :stroke="color"
      fill="transparent"
      :stroke-dasharray="circumference + ' ' + circumference"
      :style="{ strokeDashoffset }"
      :stroke-width="stroke"
      :r="normalizedRadius"
      :cx="radius"
      :cy="radius"
    />
    <text
      class="gauge-state"
      x="50%"
      y="42%"
      text-anchor="middle"
      fill="#000"
      dy="2"
    >{{`${this.progress} / ${this.steps}`}}</text>
    <text class="gauge-title" x="50%" y="55%" text-anchor="middle" fill="#000" dy="8">Completed</text>
  </svg>
</template>

<script>
    export default {
        name: 'x-progress-gauge',
        props: {
            radius: {
                type: Number,
                default: 60,
            },
            color: {
                type: String,
                default: '#0FBC18'
            },
            background: {
                type: Boolean,
                default: true
            },
            steps: {
                type: Number,
                required: true,
                validator: function( value) {
                    return value > 0
                },
            },
            stroke: {
                type: Number,
                default: 4,
            },
            progress: {
                type: Number,
                required: true,
                validator: function( value) {
                    return value >= 0
                },
            }
        },
        data() {
            const normalizedRadius = this.radius - this.stroke * 2;
            const circumference = normalizedRadius * 2 * Math.PI;

            return {
            normalizedRadius,
            circumference,
            };
        },
        computed: {
            strokeDashoffset() { 
                return this.circumference - this.progress / this.steps * this.circumference;
            }
        }
    }
</script>

<style lang="scss" scoped>
    circle {
        transition: stroke-dashoffset 0.35s;
        transform: rotate(-90deg);
        transform-origin: 50% 50%;
    }
    .gauge-state {
        font-size: 16px;
    }
    .gauge-title {
        font-size: 12px;
    }
</style>