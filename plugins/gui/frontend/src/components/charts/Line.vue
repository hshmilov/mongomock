<template>
    <div class="x-line">
        <svg viewBox="0 0 240 240">
            <template v-for="scale, i in verticalScales">
                <text class="line-text" text-anchor="middle" x="10" :dy="calcVerticalY(i)">{{ scale }}</text>
                <line class="line-scale" x1="20" x2="220" :y1="calcVerticalY(i) - 4" :y2="calcVerticalY(i) - 4"></line>
            </template>
            <template v-for="scale, i in horizontalScales">
                <text class="line-text" text-anchor="middle" :dx="calcHorizontalX(i)" y="200">{{ scale }}</text>
            </template>
            <template v-for="line, lineInd in processedData">
                <g class="line-plot" :class="{ hover: lineInd === hoverLine, [ line.class ]: true }">
                    <template v-for="segment, segmentInd in line.segments">
                        <line :x1="segment.x1" :x2="segment.x2" :y1="segment.y1" :y2="segment.y2" class="plot-segment"></line>
                        <line :x1="segment.x1" :x2="segment.x2" :y1="segment.y1" :y2="segment.y2" class="segment-margin"
                              @mouseover="mouseoverLine($event, lineInd)" @mouseout="mouseoutLine"></line>
                    </template>
                    <template v-for="segment, segmentInd in line.segments">
                        <circle :cx="segment.x2" :cy="segment.y2" r="4" class="plot-point"></circle>
                        <circle :cx="segment.x2" :cy="segment.y2" r="8" class="point-margin"
                                @mouseover="mouseoverPoint($event, lineInd, segmentInd)" @mouseout="mouseoutPoint"></circle>
                    </template>
                </g>
            </template>
        </svg>
        <div v-if="showTooltip" class="tooltip" ref="tooltip">
            <div class="tooltip-title">{{ processedData[hoverLine].title }}</div>
            <div v-if="showPoint" class="tooltip-content">
                <div class="content-title">{{ processedData[hoverLine].segments[hoverPoint].point.x }}</div>
                <div>{{ processedData[hoverLine].segments[hoverPoint].point.y }}</div>
            </div>
        </div>
    </div>
</template>

<script>
	export default {
		name: 'x-line',
        props: { data: { required: true } },
        computed : {
			processedData() {
                return this.data.map((line, lineIndex) => {
				    let prev = {x: 20, y: 190 }
                    let segments = []
                    line.points.forEach((point, index) => {
                    	let next = {
                    		x: this.calcHorizontalX(index + 1),
							y: 200 - (point.y * 180 / this.lastVerticalScale)
                        }
                        segments.push({
                            x1: prev.x, y1: prev.y, x2: next.x, y2: next.y,
                            point
                        })
                        prev = next
                    })
                    return {
				        title: line.title,
                        class: `extra-fill-${(lineIndex % 6) || 6} extra-stroke-${(lineIndex % 6) || 6}`,
                        segments
				    }
                })
            },
            horizontalScales() {
                return [ 0, 1, 2, 3, 4, 5 ]
            },
            horizontalSpace() {
            	return 240 / this.horizontalScales.length
            },
            verticalScales() {
            	return [ 0, 10, 20, 30, 40, 50, 60 ]
            },
            lastVerticalScale() {
				return this.verticalScales[this.verticalScales.length - 1]
            },
            verticalSpace() {
            	return 200 / this.verticalScales.length
            },
            showTooltip() {
                return this.processedData.length && this.hoverLine >= 0 && this.hoverLine < this.processedData.length
            },
            showPoint() {
			    if (!this.processedData.length) return
			    return this.hoverPoint >= 0 && this.hoverPoint < this.processedData[this.hoverLine].segments.length
            }
        },
        data() {
			return {
				hoverLine: -1,
                hoverPoint: -1
            }
        },
        methods: {
			calcVerticalY(index) {
				return this.verticalSpace * (this.verticalScales.length - index)
            },
            calcHorizontalX(index) {
				return 10 + (index * this.horizontalSpace)
            },
            mouseoverLine(event, index) {
				this.hoverLine = index
                if (!this.$refs || !this.$refs.tooltip) return
                this.$refs.tooltip.style.top = event.clientY + 10 + 'px'
                this.$refs.tooltip.style.left = event.clientX + 10 + 'px'
            },
            mouseoutLine() {
				this.hoverLine = -1
            },
            mouseoverPoint(event, lineIndex, pointIndex) {
                this.hoverLine = lineIndex
				this.hoverPoint = pointIndex
                if (!this.$refs || !this.$refs.tooltip) return
                this.$refs.tooltip.style.top = event.clientY + 10 + 'px'
                this.$refs.tooltip.style.left = event.clientX + 10 + 'px'
            },
            mouseoutPoint() {
				this.hoverPoint = -1
                this.hoverLine = -1
            }
        }
	}
</script>

<style lang="scss">
    .x-line {
        height: 240px;
        .line-text {
            font-size: 10px;
            fill: $grey-3;
        }
        .line-scale {
            stroke: $grey-1;
        }
        .line-plot {
            cursor: pointer;
            .plot-segment {
                stroke-width: 2px;
                opacity: 0.4;
                &.hover {
                    opacity: 1;
                }
            }
            .segment-margin {
                stroke-width: 16px;
                opacity: 0;
            }
            .plot-point {
                opacity: 0;
                &:hover {
                    opacity: 1;
                }
            }
            .point-margin {
                opacity: 0;
            }
            &.hover {
                .plot-segment {
                    opacity: 1;
                }
                .plot-point {
                    opacity: 1;
                }
            }
        }
        .tooltip {
            .content-title {
                color: $theme-blue;
                font-weight: 400;
                flex: 1 0 auto;
            }

        }
    }
</style>