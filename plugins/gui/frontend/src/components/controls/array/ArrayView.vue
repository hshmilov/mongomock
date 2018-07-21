<template>
    <div class="x-array-view">
        <div v-if="schema.title === 'SEPARATOR'" class="separator">&nbsp;</div>
        <template v-else-if="schema.title">
            <div @click="toggleCollapsed" class="x-btn link expander">{{ collapsed? '+': '-'}}</div>
            <label :title="schema.description || ''" class="label">{{ schema.title }}</label>
        </template>
        <div class="array">
            <div v-for="item, index in schemaItems" v-if="!empty(data[item.name]) && (!collapsed || !index)" class="item-container">
                <!-- In collapsed mode, only first item is revealed -->
                <div ref="item" class="item" :class="{ 'growing-y': collapsable}">
                    <div v-if="typeof item.name === 'number'" class="index">{{item.name + 1}}.</div>
                    <x-type-wrap v-bind="item" :required="true">
                        <component :is="item.type" :schema="item" :value="data[item.name]" :ref="item.type" />
                    </x-type-wrap>
                </div>
            </div>
        </div>
        <!-- Indication for more data for this item -->
        <div class="placeholder" v-if="collapsed && schemaItems.length > 1">...</div>
    </div>
</template>

<script>
	import xTypeWrap from './TypeWrap.vue'
	import string from '../string/StringView.vue'
	import number from '../numerical/NumberView.vue'
	import integer from '../numerical/IntegerView.vue'
	import bool from '../boolean/BooleanView.vue'
	import file from './FileView.vue'

    import ArrayMixin from './array'

	export default {
		name: 'array',
		mixins: [ ArrayMixin ],
		components: { xTypeWrap, string, number, integer, bool, file },
        computed: {
			collapsable() {
				return this.schema.title && this.schema.title !== 'SEPARATOR'
            }
        },
        methods: {
			updateCollapsed(collapsed) {
				if (!this.collapsable) return

				if (!collapsed) {
					this.collapsed = false
				} else if (!this.collapsed) {
					this.$refs.item.forEach((item, index) => {
						// Exit animation for items to be collapsed (all but first)
						if (index) item.classList.add('shrinking-y')
					})
					setTimeout(() => this.collapsed = true, 1000)
				}
			},
			toggleCollapsed() {
				this.updateCollapsed(!this.collapsed)
            },
            collapseRecurse(collapsed) {
                this.updateCollapsed(collapsed)
                setTimeout(() => {
                    if (!this.$refs.array) return
                    this.$refs.array.forEach(item => {
                        item.collapseRecurse(collapsed)
                    })
                })
            }
        },
        created() {
			if (this.collapsable && !Array.isArray(this.schema.items)) {
				// Collapsed by default, only for real lists (not an object with ordered fields)
				this.collapsed = true
            }
        }
	}
</script>

<style lang="scss">
    .x-array-view {
        .separator {
            width: 100%;
            height: 1px;
            background-color: rgba($theme-orange, 0.2);
            margin: 12px 0;
        }
        .x-btn.link.expander {
            display: inline-block;
            padding: 0;
            width: 20px;
            text-align: left;
        }
        .item-container {
            overflow: hidden;
        }
        .placeholder {
            margin-left: 20px;
            color: $grey-3;
            font-weight: 500;
        }
        .label, .index {
            font-weight: 500;
        }
        .index {
            margin-right: 4px;
            display: inline-block;
            vertical-align: top;
        }
    }
</style>