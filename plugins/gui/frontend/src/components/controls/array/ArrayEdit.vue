<template>
    <div class="array">
        <h4 v-if="schema.title" :title="schema.description || ''" class="header grid-span2">{{schema.title}}</h4>
        <div v-for="item in shownSchemaItems" class="item">
            <x-type-wrap :name="item.name" :type="item.type" :title="item.title" :description="item.description"
                         :required="item.required">
                <component :is="item.type" :schema="item" v-model="data[item.name]" :validator="validate"
                           @input="onInput" @focusout="onFocusout" :api-upload="apiUpload"/>
            </x-type-wrap>
        </div>
    </div>
</template>

<script>
    import Vue from 'vue'

    import xTypeWrap from './TypeWrap.vue'
    import string from '../string/StringEdit.vue'
    import number from '../numerical/NumberEdit.vue'
    import integer from '../numerical/IntegerEdit.vue'
    import bool from '../boolean/BooleanEdit.vue'
    import file from './FileEdit.vue'

    import ArrayMixin from './array'

    export default {
        name: 'array',
        mixins: [ArrayMixin],
        components: {
            xTypeWrap,
            string,
            number,
            integer,
            bool,
            file
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