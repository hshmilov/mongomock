<template>
    <div class="pie">
        <svg viewBox="-1 -1 2 2" @mouseout="inHover = -1">
            <defs>
                <linearGradient id="intersection-1-2">
                    <stop class="extra-stop-1" offset="0%"></stop>
                    <template  v-for="n in 9">
                        <stop :class="`extra-stop-${!(n % 2) ? 3 : 1}`" :offset="`${n}0%`"></stop>
                        <stop :class="`extra-stop-${!(n % 2) ? 1 : 3}`" :offset="`${n}0%`"></stop>
                    </template>
                    <stop class="extra-stop-1" offset="100%"></stop>
                </linearGradient>
            </defs>
            <g v-for="slice, index in slices" @click="$emit('click-one', index)" @mouseover="onHover($event, index)">
                <path :d="slice.path" :class="`filling ${slice.class} ${inHover === index? 'in-hover' : ''}`"></path>
                <text v-if="slice.anotate && slice.portion" class="scaling" text-anchor="middle"
                      :x="slice.middle.x" :y="slice.middle.y">{{Math.round(slice.portion * 100)}}%</text>
            </g>
        </svg>
        <div v-show="hoverTitle" ref="tooltip" class="pie-tooltip">{{hoverTitle}}</div>
    </div>
</template>

<script>
	export default {
		name: 'x-pie-chart',
        props: {data: {required: true}},
        computed: {
			completeData() {
				let sumPortions = this.data.reduce((sum, item) => {
					return sum + item.portion
				}, 0)
				if (sumPortions === 1) return this.data
				return [ {
					portion: 1 - sumPortions, anotate: false, class: 'theme-fill-gray-light'
                }, ...this.data ]
			},
			slices() {
				let cumulativePortion = 0
                return this.completeData.map((slice, index) => {
                    // Starting slice at the end of previous one, and ending after percentage defined for item
                    const [startX, startY] = this.getCoordinatesForPercent(cumulativePortion)
                    cumulativePortion += slice.portion / 2
                    const [middleX, middleY] = this.getCoordinatesForPercent(cumulativePortion)
					cumulativePortion += slice.portion / 2
                    const [endX, endY] = this.getCoordinatesForPercent(cumulativePortion)
					return {
						class: `extra-fill-${index % 6}`,  ...slice,
                        path: [
							`M ${startX} ${startY}`, // Move
							`A 1 1 0 ${slice.portion > .5 ? 1 : 0} 1 ${endX} ${endY}`, // Arc
							`L 0 0`, // Line
						].join(' '),
                        middle: { x: middleX * 0.7, y: middleY * (middleY > 0? 0.8: 0.5) }
					}
                })
            },
            hoverTitle() {
				if (this.inHover === -1) return ''
                return this.slices[this.inHover].title
            }
        },
        data() {
			return {
				inHover: -1
            }
        },
        methods: {
			getCoordinatesForPercent (portion) {
				return [
					Math.cos(2 * Math.PI * portion),
                    Math.sin(2 * Math.PI * portion)
                ]
			},
            onHover(event, index) {
				this.inHover = index
                if (!this.$refs || !this.$refs.tooltip) return
                this.$refs.tooltip.style.top = event.clientY + 20 + 'px'
				this.$refs.tooltip.style.left = event.clientX + 20 + 'px'
            }
        }
	}
</script>

<style lang="scss">
    .pie {
        margin: auto;
        width: 240px;
        .fill-intersection-1-2 {
            fill: url(#intersection-1-2)
        }
        g {
            cursor: pointer;
            path {
                opacity: 0.4;
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
    }
    .pie-tooltip {
        background-color: $theme-white;
        border: 1px solid $grey-2;
        border-radius: 2px;
        position: fixed;
        padding: 8px;
    }
</style>