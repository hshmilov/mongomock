<template>
    <svg class="x-cycle">
        <!-- Basis for the cycle - full circle, not coloured -->
        <circle class="pre" :r="radius" cx="50%" cy="50%"></circle>

        <template v-for="item, index in data">
            <!-- Slice filled according to complete portion of current item -->
            <circle :class="`slice extra-stroke-${(index % 6) + 1}`" :r="radius" cx="50%" cy="50%" v-bind:style="{
                    strokeDasharray: `${sliceLength * item.status} ${circleLength}`,
                    strokeDashoffset: -(index * sliceLength)
                }"></circle>
            <!-- Marker of 1px in the start of the slice -->
            <circle class="marker" :r="radius" cx="50%" cy="50%" v-bind:style="{
                    strokeDasharray: `4 ${circleLength}`,
                    strokeDashoffset: -(index * sliceLength)
                }"></circle>
        </template>

        <template v-if="status < 100">
            <!-- Percentage of completion of the cycle, updating while cycle proceeds -->
            <text v-if="currentStageName" x="50%" y="50%" text-anchor="middle"
                  :class="`extra-fill-${stageColourIndex} subtitle`">{{ currentStageName }}...
            </text>
            <text x="50%" y="50%" text-anchor="middle" dy="2em" class="cycle-title">{{ parseInt(status) }}%</text>
        </template>
        <template v-else>
            <!-- Cycle is complete, namely status is stable -->
            <text x="50%" y="50%" text-anchor="middle" class="cycle-title">STABLE</text>
            <path d="M160 100 L140 130 L130 120" stroke-width="4" class="check"></path>
        </template>
    </svg>
</template>

<script>
    export default {
        name: 'x-cycle',
        props: {
            data: {
                required: true
            },
            radius: {
                default: 80
            }
        },
        computed: {
            circleLength() {
                return 2 * Math.PI * this.radius
            },
            sliceCount() {
                if (!this.data) return 0
                return this.data.length
            },
            sliceLength() {
                if (!this.circleLength || !this.sliceCount) return 0
                return this.circleLength / this.sliceCount
            },
            status() {
                if (!this.data || !this.data.length) return 100
                return this.data.reduce((sum, item) => sum + item.status, 0) * 100 / this.sliceCount
            },
            currentStage() {
                if (!this.data || !this.data.length) return null
                let stage = this.data[0]
                let i = 1
                while (i < this.data.length && stage.status === 1) {
                    stage = this.data[i]
                    i++
                }
                return {...stage, index: i}
            },
            currentStageName() {
                if (!this.currentStage) return ''
                return this.currentStage.name.split('_').join(' ')
            },
            stageColourIndex() {
                if (!this.currentStage) return 1
                return (this.currentStage.index % 6)
            }
        }
    }
</script>

<style lang="scss">

    .x-cycle {
        margin: auto;
        height: 175px;

        circle {
            transition: stroke-dasharray 0.3s ease-in-out, stroke-dashoffset 0.3s ease-in-out;
            fill: none;
            stroke-width: 12;

            &.pre {
                stroke: $grey-1;
            }

            &.marker {
                stroke: $theme-white;
                stroke-width: 16;
            }

            &.post {
                stroke-width: 0;
                fill: $theme-white;
            }
        }

        text {
            stroke: none;
            font-size: 10px;

            &.cycle-title {
                fill: $grey-5;
                font-size: 24px;
            }

            &.subtitle {
                font-size: 18px;
            }
        }

        path {
            fill: none;
            stroke: none;

            &.check {
                stroke: $indicator-success;
                stroke-dasharray: 60;
                stroke-dashoffset: -60;
                animation: check-stroke ease-in-out .8s forwards;
            }
        }
    }

    @keyframes check-stroke {
        100% {
            stroke-dashoffset: 0;
        }
    }

</style>