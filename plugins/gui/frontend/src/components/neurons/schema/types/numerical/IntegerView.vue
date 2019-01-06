<template>
    <div :class="severity">
        <a v-if="hyperlink" :href="hyperlink.href" @click="onClickLink(hyperlink)">{{ displaying }}</a>
        <template v-else>
            {{ displaying }}
        </template>
    </div>
</template>

<script>
    import HyperlinkMixin from '../hyperlink.js'
    import {mapState} from 'vuex'

    export default {
        name: 'x-integer-view',
        props: ['schema', 'value'],
        mixins: [HyperlinkMixin],
        computed: {
            ...mapState({
                percentageThresholds(state) {
                    if (!state.configuration || !state.configuration.data || !state.configuration.data.system) {
                        return []
                    }
                    return state.configuration.data.system.percentageThresholds
                }
            }),
            processedData() {
                if (Array.isArray(this.value)) {
                    return this.value.map(item => this.format(item)).join(', ')
                }
                return this.format(this.value)
            },
            isPercentage() {
                return this.schema.format && this.schema.format === 'percentage'
            },
            severity() {
                if (this.value === undefined || this.value === null || !this.isPercentage) return ''

                let minDiff = 101
                let minSeverity = ''
                Object.keys(this.percentageThresholds).forEach(thresholdName => {
                    if (this.percentageThresholds[thresholdName] < this.value) return
                    let diff = this.percentageThresholds[thresholdName] - this.value
                    if (diff < minDiff) {
                        minDiff = diff
                        minSeverity = thresholdName
                    }
                })
                return minSeverity
            },
            displaying() {
                return `${this.processedData}${this.isPercentage && this.processedData ? '%' : ''}`
            }
        },
        methods: {
            format(value) {
                if (typeof value === 'number') {
                    return parseInt(value)
                }
                return ''
            }
        }
    }
</script>

<style lang="scss">

</style>