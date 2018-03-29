<template>
    <svg class="pie" viewBox="-1 -1 2 2">
        <g v-for="item, index in slices" @click="$emit('click-slice', index)">
            <path :d="item.path" :class="item.class" class="filling clickable"></path>
            <text dx="1.5em" dy="1em" text-anchor="middle" class="scaling" v-if="item.percentage">{{item.percentage}}%</text>
        </g>
    </svg>
</template>

<script>
	export default {
		name: 'x-pie-chart',
        props: {data: {required: true}},
        computed: {
			slices() {
				let cumulativePortion = 0
                return this.data.map((slice, index) => {
                    // Starting slice at the end of previous one, and ending after percentage defined for item
                    const [startX, startY] = this.getCoordinatesForPercent(cumulativePortion)
                    cumulativePortion += slice.portion
                    const [endX, endY] = this.getCoordinatesForPercent(cumulativePortion)
					return {
						class: `extra-fill-${(index % 6) + 1}`,  ...slice,
                        path: [
							`M ${startX} ${startY}`, // Move
							`A 1 1 0 ${slice.portion > .5 ? 1 : 0} 1 ${endX} ${endY}`, // Arc
							`L 0 0`, // Line
						].join(' ')
					}
                })
            },
        },
        methods: {
			getCoordinatesForPercent (portion) {
				return [
					Math.cos(2 * Math.PI * portion),
                    Math.sin(2 * Math.PI * portion)
                ];
			}
        }
	}
</script>

<style lang="scss">
    .pie {
        margin: auto;
        path, text {
            cursor: pointer;
        }
        .clickable {
            opacity: 0.6;
            transition: opacity ease-in 0.4s;
            &:hover {
                opacity: 1;
            }
        }
        text {
            font-size: 2%;
            fill: $theme-black;
        }
    }
</style>