<template>
        <svg class="cycle">
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
                <text v-if="stageName" x="50%" y="50%" text-anchor="middle"
                      :class="`extra-fill-${(stageIndex % 6) + 1}`">{{stageName}}...</text>
                <text x="50%" y="50%" text-anchor="middle" dy="2em" class="subtitle">{{parseInt(status)}}%</text>
            </template>
            <template v-else>
                <!-- Cycle is complete, namely status is stable -->
                <text x="50%" y="50%" text-anchor="middle" class="title">STABLE</text>
                <path d="M170 130 L140 160 L130 150" stroke-width="4" class="check"></path>
            </template>
        </svg>
</template>

<script>
	export default {
		name: 'x-cycle-chart',
        props: {data: {required: true}, radius: {default: 100}},
        computed: {
			circleLength() {
                return 2 * Math.PI * this.radius
            },
            sliceCount() {
				if (!this.data) return 0
				return this.data.length
            },
            sliceLength() {
				if (!this.circleLength|| !this.sliceCount) return 0
                return this.circleLength / this.sliceCount
            },
            status() {
				if (!this.data || !this.data.length) return 100
				return this.data.reduce((sum, item) => sum + item.status, 0) * 100 / this.sliceCount
            },
            stageName() {
				if (!this.data || !this.data.length) return ''
                return this.data.filter(item => (item.status > 0) && (item.status < 1))[0].name.split('_').join(' ')
            },
            stageIndex() {
				if (!this.data || !this.data.length) return -1
                let currentStage = -1
				this.data.forEach((item, index) => {
					if (item.status > 0 && item.status < 1) {
						currentStage = index
                    }
                })
                return currentStage
            }
        }
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .cycle {
        margin: auto;
        circle {
            transition: stroke-dasharray 0.3s ease-in-out,stroke-dashoffset 0.3s ease-in-out;
            fill: none;
            stroke-width: 12;
            &.pre {
                stroke: $theme-gray-light;
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
            fill: $theme-gray-dark;
            font-size: 10px;
            &.title {
                fill: $theme-blue;
                font-size: 18px;
            }
            &.subtitle {
                font-size: 24px;
            }
        }
        path {
            fill: none;
            stroke: none;
            &.check {
                stroke: $indicator-green;
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