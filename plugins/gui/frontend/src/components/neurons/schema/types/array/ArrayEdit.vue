<template>
    <div class="array">
        <h4 v-if="schema.title" :title="schema.description || ''" class="array-header"
            :id="schema.name">{{ schema.title }}</h4>
        <div v-for="(item, index) in shownSchemaItems" class="item">
            <div v-if="!isOrderedObject" class="x-btn link" @click="removeItem(index)">x</div>
            <x-type-wrap :name="item.name" :type="item.type" :title="item.title" :description="item.description"
                         :required="item.required">
                <component :is="item.type" :schema="item" v-model="data[item.name]" @validate="onValidate"
                           @input="onInput" :api-upload="apiUpload" ref="itemChild" :read-only="readOnly" />
            </x-type-wrap>
        </div>
        <button v-if="!isOrderedObject" class="x-btn light" @click.prevent="addNewItem">+</button>
    </div>
</template>

<script>
    import xTypeWrap from './TypeWrap.vue'
    import string from '../string/StringEdit.vue'
    import number from '../numerical/NumberEdit.vue'
    import integer from '../numerical/IntegerEdit.vue'
    import bool from '../boolean/BooleanEdit.vue'
    import file from './FileEdit.vue'
    import range from '../string/RangeEdit.vue'

    import ArrayMixin from './array'

    export default {
        name: 'array',
        mixins: [ArrayMixin],
        props: { readOnly: { default: false } },
        components: {
            xTypeWrap, string, number, integer, bool, file, range
        },
        data() {
        	return {
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
            },
            addNewItem() {
                this.data[Object.keys(this.data).length] = this.schema.items.items.reduce((map, field) => {
                    map[field.name] = field.default || null
                    return map
                }, {})
                this.onInput()
            },
            removeItem(index) {
                delete this.data[index]
                this.onInput()
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
        .array-header {
            margin-bottom: 0;
            display: inline-block;
            min-width: 200px;
        }
        .item {
            .index {
                display: inline-block;
                vertical-align: top;
            }
            .x-btn.link {
                text-align: right;
            }
        }
    }
</style>