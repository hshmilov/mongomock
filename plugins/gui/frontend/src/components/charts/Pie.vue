<template>
    <div class="pie" :id="id">
        <svg viewBox="-1 -1 2 2" @mouseout="inHover = -1">
            <defs>
                <linearGradient id="intersection-1-2">
                    <stop class="extra-stop-1" offset="0%"></stop>
                    <template v-for="n in 9">
                        <stop :class="`extra-stop-${!(n % 2) ? 3 : 1}`" :offset="`${n}0%`"></stop>
                        <stop :class="`extra-stop-${!(n % 2) ? 1 : 3}`" :offset="`${n}0%`"></stop>
                    </template>
                    <stop class="extra-stop-3" offset="100%"></stop>
                </linearGradient>
            </defs>
            <g v-for="slice, index in slices" @click="$emit('click-one', index)" @mouseover="onHover($event, index)"
               :id="getId(index)">
                <path :d="slice.path" :class="`filling ${slice.class} ${inHover === index? 'in-hover' : ''}`"></path>
            </g>
        </svg>
        <div v-show="hoverDetails.title" ref="tooltip" class="pie-tooltip">
            <div class="tooltip-title">{{ hoverDetails.parentTitle }}</div>
            <div class="tooltip-content">
                <div class="tooltip-legend">
                    <div class="legend" :class="hoverDetails.class"></div>
                    {{ hoverDetails.title }}
                </div>
                <div>{{ hoverDetails.percentage }}%</div>
            </div>
            <div class="tooltip-content" v-for="component in hoverDetails.components">
                <div class="tooltip-legend">
                    <div class="legend round" :class="component.class"></div>
                    {{ component.title }}
                </div>
            </div>
        </div>
    </div>
</template>

<script>
	export default {
		name: 'x-pie-chart',
		props: {data: {required: true}, id: {}},
		computed: {
			completeData () {
				let sumPortions = this.data.reduce((sum, item) => {
					return sum + item.portion
				}, 0)
				if (sumPortions === 1) return this.data
				return [{
					portion: 1 - sumPortions, class: 'theme-fill-gray-light'
				}, ...this.data]
			},
			slices () {
				let cumulativePortion = 0
				return this.completeData.map((slice) => {
					// Starting slice at the end of previous one, and ending after percentage defined for item
					const [startX, startY] = this.getCoordinatesForPercent(cumulativePortion)
					cumulativePortion += slice.portion / 2
					cumulativePortion += slice.portion / 2
					const [endX, endY] = this.getCoordinatesForPercent(cumulativePortion)
					return {
						...slice,
						path: [
							`M ${startX} ${startY}`, // Move
							`A 1 1 0 ${slice.portion > .5 ? 1 : 0} 1 ${endX} ${endY}`, // Arc
							`L 0 0`, // Line
						].join(' ')
					}
				})
			},
			hoverDetails () {
				if (this.inHover === -1) return {}
				let percentage = Math.round(this.completeData[this.inHover].portion * 100)
				if (percentage < 0) {
					percentage = 100 + percentage
				}
				let title = this.completeData[this.inHover].title
				let components = []
				if (Array.isArray(title)) {
					title = 'Intersection'
					components.push({...this.completeData[this.inHover - 1]})
					components.push({...this.completeData[this.inHover + 1]})
				}
				return {
					parentTitle: this.data[0].title, title, percentage, class: this.completeData[this.inHover].class,
					components
				}
			}
		},
		data () {
			return {
				inHover: -1
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
			getId (name) {
				if (!this.id) return undefined

				return `${this.id}_${name}`
			}
		}
	}
</script>

<style lang="scss">
    .pie {
        margin: auto;
        width: 240px;
        .fill-intersection-1-2 {
            fill: url(#intersection-1-2);
            background: repeating-linear-gradient(45deg, nth($extra-colours, 1), nth($extra-colours, 1) 4px,
                    nth($extra-colours, 2) 4px, nth($extra-colours, 2) 8px
            );
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
    }

    .pie-tooltip {
        background-color: $theme-white;
        border: 1px solid $grey-2;
        border-radius: 2px;
        position: fixed;
        padding: 12px;
        z-index: 1000;
        max-width: 300px;
        .tooltip-title {
            color: $grey-3;
        }
        .tooltip-content {
            display: flex;
            .tooltip-legend {
                margin-right: 12px;
                flex: 1 0 auto;
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