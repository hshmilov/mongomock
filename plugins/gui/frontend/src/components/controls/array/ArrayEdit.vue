<template>
    <div class="array">
        <h4 v-if="schema.title" :title="schema.description || ''" class="header grid-span2" :id="schema.name">
            {{ schema.title }}
        </h4>
        <div v-for="item in shownSchemaItems" class="item">
            <x-type-wrap :name="item.name" :type="item.type" :title="item.title" :description="item.description"
                         :required="item.required">
                <component :is="item.type" :schema="item" v-model="data[item.name]" @validate="onValidate"
                           @input="onInput" :api-upload="apiUpload" ref="itemChild" />
            </x-type-wrap>
        </div>
    </div>
</template>

<script>
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
            xTypeWrap, string, number, integer, bool, file
        },
        data() {
        	return {
				data: { ...this.value },
                needsValidation: false
            }
        },
        methods: {
            onInput() {
                this.$emit('input', this.data)
            },
            onValidate(validity) {
                this.$emit('validate', validity)
            },
            validate(silent) {
            	if (!this.$refs.itemChild) return
                this.$refs.itemChild.forEach(item => item.validate(silent))
            }
        },
        watch: {
        	isHidden() {
        		/*
        		    Change of hidden, means some fields may appear or disappear.
        		    Therefore, the new children should be re-validated but the DOM has not updated yet
        		 */
        		this.needsValidation = true
            }
        },
        mounted() {
            this.validate(true)
        },
        updated() {
        	if (this.needsValidation) {
        		// Here the new children (after change of hidden) are updated in the DOM
				this.validate(true)
                this.needsValidation = false
            }
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