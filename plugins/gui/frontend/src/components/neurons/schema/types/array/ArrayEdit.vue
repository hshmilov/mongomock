<template>
    <div class="x-array-edit">
        <template v-if="!isItemsString">
            <h4 v-if="schema.title" :title="schema.description || ''" class="array-header"
                :id="schema.name">{{ schema.title }}</h4>
            <div v-for="(item, index) in shownSchemaItems" class="item">
                <x-type-wrap :name="item.name" :type="item.type" :title="item.title" :description="item.description"
                             :required="item.required">
                    <component :is="item.type" :schema="item" v-model="data[item.name]" @validate="onValidate"
                               :api-upload="apiUpload" ref="itemChild" :read-only="readOnly" />
                </x-type-wrap>
                <x-button link v-if="!isOrderedObject" @click.prevent="removeItem(index)">x</x-button>
            </div>
            <x-button v-if="!isOrderedObject" light @click.prevent="addNewItem">+</x-button>
        </template>
        <template v-else >
            <label>{{schema.title}}</label>
            <md-chips v-model="data" md-placeholder="Add..." />
        </template>
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
    import xButton from '../../../../axons/inputs/Button.vue'

    import arrayMixin from './array'

    export default {
        name: 'array',
        mixins: [arrayMixin],
        props: { readOnly: { default: false } },
        components: {
            xTypeWrap, string, number, integer, bool, file, range, xButton
        },
        data() {
        	return {
                needsValidation: false
            }
        },
        computed: {
            isItemsString() {
                if (this.isOrderedObject) return false
                return this.schema.items.type === 'string'
            }
        },
        methods: {
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
            },
            removeItem(index) {
                delete this.data[index]
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
    .x-array-edit {
        .array-header {
            margin-bottom: 0;
            display: inline-block;
            min-width: 200px;
        }
        .item {
            display: flex;
            align-items: flex-end;
            .index {
                display: inline-block;
                vertical-align: top;
            }
            .x-button.link {
                text-align: right;
            }
        }
    }
</style>