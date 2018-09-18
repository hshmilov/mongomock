<template>
    <table class="x-striped-table">
        <thead>
            <tr class="x-row clickable">
                <th v-if="value" class="w-14">
                    <x-checkbox v-model="allSelected" :semi="allSelected && selected.length !== data.length"
                                @change="updateAllSelected"/>
                </th>
                <th v-for="field in fields" nowrap :class="{sortable: clickColHandler}"
                    @click="clickCol(field.name)" @keyup.enter.stop="clickCol(field.name)">

                    <img v-if="field.logo" class="logo" :src="`/src/assets/images/logos/${field.logo}.png`" height="20">
                    {{ field.title }}<div v-if="clickColHandler" :class="`x-sort ${sortClass(field.name)}`"></div>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr v-for="item in data" @click="clickRow(item[idField])" :id="item[idField]"
                class="x-row" :class="{ clickable: clickRowHandler }">
                <td v-if="value" class="w-14">
                    <x-checkbox v-model="selected" :value="item[idField]" @change="updateSelected" />
                </td>
                <td v-for="field in fields" nowrap>
                    <component :is="field.type" :schema="field" :value="processDataValue(item, field)" />
                </td>
            </tr>
            <template v-if="pageSize">
                <tr v-for="n in pageSize - data.length" class="x-row">
                    <td v-if="value">&nbsp;</td>
                    <td v-for="field in fields">&nbsp;</td>
                </tr>
            </template>
        </tbody>
    </table>
</template>

<script>
    import xCheckbox from '../inputs/Checkbox.vue'
	import string from '../controls/string/StringView.vue'
	import number from '../controls/numerical/NumberView.vue'
	import integer from '../controls/numerical/IntegerView.vue'
	import bool from '../controls/boolean/BooleanView.vue'
	import file from '../controls/array/FileView.vue'
	import array from '../controls/array/ArrayInlineView.vue'

	export default {
		name: 'x-table',
        components: { xCheckbox, string, integer, number, bool, file, array },
        props: {
			fields: {}, data: {}, pageSize: {}, sort: {}, idField: { default: 'id' }, value: {},
            clickRowHandler: {}, clickColHandler: {}
        },
        computed: {
		    ids() {
		    	return this.data.map(item => item[this.idField])
		    }
		},
        data() {
			return {
                selected: [],
                allSelected: false
            }
        },
        watch: {
			value(newValue) {
				this.selected = [ ...newValue ]
                if (!this.selected.length) {
					this.allSelected = false
                }
            }
        },
        methods: {
			clickRow(id) {
				if (!this.clickRowHandler) return

                this.clickRowHandler(id)
            },
            clickCol(name) {
				if (!this.clickColHandler) return

                this.clickColHandler(name)

            },
            sortClass(name) {
                if (this.sort.field !== name) return ''
                if (this.sort.desc) return 'down'
                return 'up'
            },
            updateAllSelected() {
				let input = {ids: []}
				if (this.allSelected) {
					this.selected = [ ...this.ids ]
                    input.included = false
                } else {
					this.selected = []
					input.included = true
                }
                this.$emit('input', this.selected)
            },
            updateSelected() {
				this.$emit('input', this.selected)
                // if (this.allSelected) {
					// this.$emit('input', {
					// 	ids: this.ids.filter(item => !this.selected.includes(item)), included: false
					// })
                // } else {
                //     this.$emit('input', {ids: this.selected, included: true})
                // }
            },
            processDataValue(item, field) {
			    if (Array.isArray(item[field.name]) && field.name === this.sort.field && !this.sort.desc) {
                    return [...item[field.name]].reverse()
                }
			    return field.name.split('->').reduce((item, field_segment) => item[field_segment], item)
            }
        }
	}
</script>

<style lang="scss">
    .x-striped-table {
        background: $theme-white;
        border-collapse: collapse;
        thead {
            tr {
                border-bottom: 2px dashed $grey-2;
            }
        }
        tbody {
            tr .svg-bg {
                fill: $theme-white;
            }
            tr:nth-child(odd) {
                background: rgba($grey-1, 0.6);
                .svg-bg {
                    fill: rgba($grey-1, 0.6);
                }
            }
        }
        .x-row {
            height: 30px;
            &.clickable:hover {
                cursor: pointer;
                box-shadow: 0 2px 16px -4px $grey-4;
            }
            .item > div {
                display: inline;
            }
            .array {
                height: 24px;
            }
        }
    }
</style>