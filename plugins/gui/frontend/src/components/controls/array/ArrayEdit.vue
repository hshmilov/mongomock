<template>
    <div class="array">
        <h4 v-if="schema.title" :title="schema.description || ''" class="header grid-span2">{{schema.title}}</h4>
        <div v-for="item in shownSchemaItems" class="item">
            <x-type-wrap :name="item.name" :type="item.type" :title="item.title" :description="item.description"
                         :required="item.required">
                <component :is="`x-${item.type}-edit`" :schema="item" v-model="data[item.name]"
                           @input="onInput" :validator="validate" @focusout="onFocusout" :api-upload="apiUpload"/>
            </x-type-wrap>
        </div>
    </div>
</template>

<script>
    import Vue from 'vue'

    import xTypeWrap from './TypeWrap.vue'
    import xStringEdit from '../string/StringEdit.vue'
    import xNumberEdit from '../numerical/NumberEdit.vue'
    import xIntegerEdit from '../numerical/IntegerEdit.vue'
    import xBoolEdit from '../boolean/BooleanEdit.vue'
    import xFileEdit from './FileEdit.vue'

    import ArrayMixin from './array'

    export default {
        name: 'x-array-edit',
        mixins: [ArrayMixin],
        components: {
            xTypeWrap,
            xStringEdit,
            xNumberEdit,
            xIntegerEdit,
            xBoolEdit,
            xFileEdit
        },
        computed: {
            validate() {
                if (this.validator) return this.validator

                return new Vue()
            },
        },
        methods: {
            onFocusout() {
                this.validate.$emit('focusout')
            },
            onInput() {
                this.$emit('input', this.data)
            },
        },
        created() {
            this.validate.$on('validate', (valid) => this.$emit('validate', valid))
        }
    }
</script>

<style lang="scss">
    .array {
        .header {
            margin-bottom: 0;
        }
        .item {
            .index {
                display: inline-block;
                vertical-align: top;
            }
        }
    }
</style>