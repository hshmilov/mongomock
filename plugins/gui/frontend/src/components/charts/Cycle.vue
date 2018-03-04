<template>
        <svg class="cycle" width="200" height="212">
            <!-- Basis for the cycle - full circle, not coloured -->
            <circle class="pre" :r="radius" cx="50%" cy="50%"></circle>

            <template v-for="item, index in data">
                <!-- Slice filled according to complete portion of current item -->
                <circle class="slice" :r="radius" cx="50%" cy="50%" v-bind:style="{
                    strokeDasharray: `${sliceLength * item.status} ${circleLength}`,
                    strokeDashoffset: -(index * sliceLength)
                }"></circle>
                <!-- Marker of 1px in the start of the slice -->
                <circle class="marker" :r="radius" cx="50%" cy="50%" v-bind:style="{
                    strokeDasharray: `1 ${circleLength}`,
                    strokeDashoffset: -(index * sliceLength)
                }"></circle>
                <!-- Path tracing the entire slice, slightly wider, for placing text around it -->
                <path :d="calculateArc(index)" :id="item.name" transform="rotate(2 100 108)"></path>
                <!-- Text with the name of the item, clung to the arc path -->
                <text><textPath :xlink:href="`#${item.name}`">{{item.name.split('_').join(' ')}}</textPath></text>
            </template>

            <!-- Closure for the cycle - fill surface white, to hide markers' edges -->
            <circle class="post" :r="radius - 6" cx="50%" cy="50%"></circle>

            <template v-if="status < 100">
                <!-- Percentage of completion of the cycle, updating while cycle proceeds -->
                <text x="50%" y="50%" text-anchor="middle" dy=".5em" class="title">{{parseInt(status)}}%</text>
            </template>
            <template v-else>
                <!-- Cycle is complete, namely status is stable -->
                <text x="50%" y="50%" text-anchor="middle" class="title">STABLE</text>
                <path d="M124 124 L96 148 L84 134" stroke-width="4" class="check"></path>
            </template>
        </svg>
</template>

<script>
	export default {
		name: 'x-cycle-chart',
        props: {data: {required: true}, radius: {default: 80}},
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
            sliceAngle() {
				if (!this.sliceCount) return 0
				return 360 / this.sliceCount
            },
            status() {
				if (!this.data || !this.data.length) return 100
				return this.data.reduce((sum, item) => sum + item.status, 0) * 100 / this.sliceCount
            }
        },
        methods: {
			polarToCartesian(angleInDegrees) {
				let angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0
				return {
					x: 100 + ((this.radius + 8) * Math.cos(angleInRadians)),
					y: 108 + ((this.radius + 8) * Math.sin(angleInRadians))
				}
            },
			calculateArc(index) {
				/* Calculate d sequence for an arc, parallel to the cycle slice of given index */
				const start = this.polarToCartesian(90 + (index * this.sliceAngle))
                const end = this.polarToCartesian(90 + ((index + 1) * this.sliceAngle))

				return [
					"M", start.x, start.y,
					"A", this.radius, this.radius, 0, 0, 1, end.x, end.y
				].join(" ")
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
                stroke: $gray-light;
            }
            &.slice {
                stroke: $success-colour;
            }
            &.marker {
                stroke: $gray-dark;
                stroke-width: 36;
            }
            &.post {
                stroke-width: 0;
                fill: $white;
            }
        }
        text {
            stroke: none;
            fill: $gray-dark;
            font-size: 10px;
            &.title {
                fill: $blue;
                font-size: 36px;
            }
        }
        path {
            fill: none;
            stroke: none;
            &.check {
                stroke: $success-colour;
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