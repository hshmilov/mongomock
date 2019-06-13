<template>
    <g-chart type="LineChart" :data="processedData" :options="chartOptions" class="x-line"/>
</template>

<script>
    import {GChart} from 'vue-google-charts'

    export default {
        name: 'x-line',
        components: {GChart},
        props: {data: {required: true}},
        computed: {
            processedData() {
                return [
                    this.data[0],
                    ...this.data.slice(1).map((row) => {
                        return [new Date(row[0]), ...row.slice(1)]
                    })
                ]
            },
            chartOptions() {
                return {
                    chartArea: {
                        width: '100%', height: '80%'
                    },
                    colors: ['#15C59E', '#1593C5', '#8A32BB'],
                    vAxis: {
                        textPosition: 'in',
                        textStyle: {
                            fontSize: 12
                        }
                    },
                    hAxis: {
                        textPosition: 'out',
                        slantedText: false,
                        textStyle: {
                            fontSize: 12
                        },
                        gridlines: {
                            color: '#DEDEDE'
                        }
                    },
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        textStyle: {
                            fontSize: 12
                        },
                        showColorCode: true,
                        ignoreBounds: true,
                        isHtml: true
                    },
                    interpolateNulls: true
                }
            }
        }
    }
</script>

<style lang="scss">
    .x-line {
        height: 240px;
    }
</style>