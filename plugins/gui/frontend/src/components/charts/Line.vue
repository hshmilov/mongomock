<template>
    <div class="x-line">
        <div class="subtitle">Results for range {{ scale[0] }} - {{ scale[scale.length -1]}}:</div>
        <svg :viewBox="`0 0 ${viewWidth} ${viewHeight}`">
            <template v-for="scale, i in verticalScale">
                <!-- The quantity of each vertical scale, along with a horizontal line to mark it -->
                <text class="line-text" text-anchor="middle" :x="textOffset" :dy="calcVerticalY(i)">{{ scale }}</text>
                <line class="line-scale" :x1="scaleOffset" :x2="viewWidth - textOffset"
                      :y1="calcVerticalY(i) - textOffset" :y2="calcVerticalY(i) - textOffset"></line>
            </template>
            <template v-for="(line, lineInd) in processedData">
                <!-- Plotting one of the given lines -->
                <g class="line-plot" :class="{ hover: lineInd === hoverLine, [ line.class ]: true }">
                    <!-- Drawing the line segments first, so their hover is prioritized after all points' hover -->
                    <template v-for="segment in line.segments" v-if="segment.x1 && segment.y1">
                        <line :x1="segment.x1" :x2="segment.x2" :y1="segment.y1" :y2="segment.y2" class="plot-segment"></line>
                        <!-- Transparent thicker line, so hover triggers tooltip easily -->
                        <line :x1="segment.x1" :x2="segment.x2" :y1="segment.y1" :y2="segment.y2" class="segment-margin"
                              @mouseover="mouseoverLine($event, lineInd)" @mouseout="mouseoutLine"></line>
                    </template>
                    <template v-for="(segment, segmentInd) in line.segments">
                        <circle :cx="segment.x2" :cy="segment.y2" r="2" class="plot-point"></circle>
                        <!-- Transparent thicker circle, so hover triggers tooltip easily -->
                        <circle :cx="segment.x2" :cy="segment.y2" r="8" class="point-margin"
                                @mouseover="mouseoverPoint($event, lineInd, segmentInd)" @mouseout="mouseoutPoint"></circle>
                    </template>
                </g>
            </template>
        </svg>
        <div v-show="showTooltip" class="tooltip" ref="tooltip">
            <!-- Title of the specific line being hovered -->
            <div class="tooltip-title" v-if="showTooltip">{{ processedData[hoverLine].title }}</div>
            <div v-if="showPoint" class="tooltip-content">
                <!-- Title for the point is the horizontal scale name -->
                <div class="content-title">{{ processedData[hoverLine].segments[hoverPoint].point.x }}</div>
                <!-- Value for the title is the vertical quantity -->
                <div>{{ processedData[hoverLine].segments[hoverPoint].point.y }}</div>
            </div>
        </div>
    </div>
</template>

<script>
    export default {
        name: 'x-line',
        props: {data: {required: true}, scale: {required: true}},
        computed: {
            viewWidth() {
                return 240
            },
            viewHeight() {
                return 180
            },
            textOffset() {
                return 4
            },
            scaleOffset() {
                return 16
            },
            processedData() {
                let lastVerticalScale = this.verticalScale[this.verticalScale.length - 1]
                return this.data.map((line, lineIndex) => {
                    // Starting point that will not be drawn
                    let prev = { x: 0, y: 0 }
                    let segments = []
                    line.points.forEach((point, index) => {
                        let next = {
                            x: this.calcHorizontalX(index + 1),
                            y: this.viewHeight - this.textOffset - (point.y * (this.viewHeight - this.verticalSpace) / lastVerticalScale)
                        }
                        segments.push({
                            x1: prev.x, y1: prev.y, x2: next.x, y2: next.y,
                            point
                        })
                        prev = next
                    })
                    let colourIndex = (lineIndex % 6) || 6
                    return {
                        title: line.title, segments,
                        class: `extra-fill-${colourIndex} extra-stroke-${colourIndex}`
                    }
                })
            },
            verticalScale() {
                // Find highest result
                let maxResult = -1
                this.data.forEach((line) => {
                    line.points.forEach((point) => {
                        if (point.y > maxResult) {
                            maxResult = point.y
                        }
                    })
                })
                // Round up to nearest number that divides by 5
                while (maxResult % 5 !== 0) {
                    maxResult++
                }
                // Generate a scale of 6 evenly spread numbers up to maxResult
                return [...Array(6).keys()].map(key => key * maxResult / 5)
            },
            verticalSpace() {
                return this.viewHeight / this.verticalScale.length
            },
            horizontalSpace() {
                return (this.viewWidth - this.scaleOffset) / this.scale.length
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
                return this.verticalSpace * (this.verticalScale.length - index)
            },
            calcHorizontalX(index) {
                return (index * this.horizontalSpace)
            },
            mouseoverLine(event, index) {
                this.hoverLine = index
                this.positionTooltip()
            },
            mouseoutLine() {
                this.hoverLine = -1
            },
            mouseoverPoint(event, lineIndex, pointIndex) {
                this.hoverLine = lineIndex
                this.hoverPoint = pointIndex
                this.positionTooltip()
            },
            mouseoutPoint() {
                this.hoverPoint = -1
                this.hoverLine = -1
            },
            positionTooltip() {
                if (!this.$refs || !this.$refs.tooltip) return
                this.$refs.tooltip.style.top = event.clientY + 10 + 'px'
                this.$refs.tooltip.style.left = event.clientX + 10 + 'px'
            }
        }
    }
</script>

<style lang="scss">
    .x-line {
        height: 240px;
        .line-text {
            font-size: 8px;
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