<template>
    <div class="x-chart-metric">
        <label>Module for chart:</label>
        <x-select-symbol :options="entities" v-model="config.entity" type="icon" placeholder="module..." id="module"
                         @input="$emit('state')" class="grid-span2"/>

        <label>Base Query:</label>
        <x-select :options="views[config.entity]" :searchable="true" v-model="config.base"
                  placeholder="query (or empty for all)" id="baseQuery" class="grid-span2"/>

        <label>Intersecting Query:</label>
        <x-select :options="views[config.entity]" :searchable="true" v-model="config.intersecting[0]"
                  placeholder="query..." id="intersectingFirst" @input="$emit('state')" class="grid-span2"/>
        <template v-if="config.intersecting.length > 1">
            <label>Intersecting Query:</label>
            <x-select :options="views[config.entity]" :searchable="true" v-model="config.intersecting[1]"
                      placeholder="query..." id="intersectingSecond" @input="$emit('state')"/>
            <x-button link @click="removeIntersecting(1)">x</x-button>
        </template>
        <x-button light :disabled="hasMaxViews" class="grid-span3" @click="addIntersecting" :title="addBtnTitle">+</x-button>
    </div>
</template>

<script>
    import xButton from '../../axons/inputs/Button.vue'
    import xSelect from '../../axons/inputs/Select.vue'
    import xSelectSymbol from '../../neurons/inputs/SelectSymbol.vue'
    import chartMixin from './chart'

    export default {
        name: 'x-chart-intersect',
        components: {xButton, xSelect, xSelectSymbol},
        mixins: [chartMixin],
        props: {value: {}, views: {required: true}},
        computed: {
            hasMaxViews() {
                if (!this.max) return false
                return this.config.intersecting.length === this.max
            }
        },
        data() {
            return {
                config: {entity: '', base: '', intersecting: ['', '']},
                max: 2
            }
        },
        methods: {
            removeIntersecting(index) {
                this.config.intersecting = this.config.intersecting.filter((item, i) => i !== index)
            },
            addIntersecting() {
                this.config.intersecting.push('')
            },
            validate() {
                this.$emit('validate', !this.config.intersecting.filter(view => view === '').length)
            }
        }
    }
</script>

<style lang="scss">

</style>