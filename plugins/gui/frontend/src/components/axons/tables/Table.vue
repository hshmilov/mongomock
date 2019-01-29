<template>
    <table class="x-striped-table">
        <thead>
            <tr class="x-row clickable">
                <th v-if="value" class="w-14">
                    <x-checkbox :data="allSelected" :indeterminate="partSelected" @change="onSelectAll"/>
                </th>
                <th v-for="field in dataField" nowrap :class="{sortable: clickColHandler}"
                    @click="clickCol(field.name)" @keyup.enter.stop="clickCol(field.name)">

                    <img v-if="field.logo" class="logo md-image" :src="require(`Logos/${field.logo}.png`)" height="20">
                    {{ field.title }}<div v-if="clickColHandler" :class="`x-sort ${sortClass(field.name)}`"></div>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr v-for="item in data" @click="clickRow(item[idField])" :id="item[idField]"
                class="x-row" :class="{ clickable: clickRowHandler && !readOnly.includes(item[idField]) }">
                <td v-if="value" class="w-14">
                    <x-checkbox v-model="selected" :value="item[idField]" @change="onSelect"
                                :read-only="readOnly.includes(item[idField])" />
                </td>
                <td v-for="field in dataField" nowrap>
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
	import string from '../../neurons/schema/types/string/StringView.vue'
	import number from '../../neurons/schema/types/numerical/NumberView.vue'
	import integer from '../../neurons/schema/types/numerical/IntegerView.vue'
	import bool from '../../neurons/schema/types/boolean/BooleanView.vue'
	import file from '../../neurons/schema/types/array/FileView.vue'
	import array from '../../neurons/schema/types/array/ArrayInlineView.vue'

	export default {
		name: 'x-table',
        components: { xCheckbox, string, integer, number, bool, file, array },
        props: {
			fields: {}, data: {}, pageSize: {}, sort: {}, idField: { default: 'id' }, value: {},
            clickRowHandler: {}, clickColHandler: {}, clickAllHandler: {},
            readOnly: { type: Array, default: () => {return []} }
        },
        computed: {
		    ids() {
		    	return this.data.map(item => item[this.idField])
		    },
            allSelected() {
		        return this.selected.length && this.selected.length === this.data.length
            },
            partSelected() {
		        return this.selected.length && this.selected.length < this.data.length
            },
            dataField() {
                return this.fields.map(field => {return {...field, path: (field.path ? field.path : []).concat([field.name])}})
            },
		},
        data() {
			return {
                selected: []
            }
        },
        watch: {
			value(newValue) {
				this.selected = [ ...newValue ]
            }
        },
        methods: {
			clickRow(id) {
				if (!this.clickRowHandler || this.readOnly.includes(id)) return

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
            onSelectAll(isSelected) {
				if (isSelected && !this.selected.length) {
					this.selected = [ ...this.ids.filter(id => !this.readOnly.includes(id)) ]
                } else {
					this.selected = []
                }
                this.$emit('input', this.selected)
                if (this.clickAllHandler) {
                    this.clickAllHandler(isSelected)
                }
            },
            onSelect() {
				this.$emit('input', this.selected)
            },
            processDataValue(item, field) {
			    if (Array.isArray(item[field.name]) && this.sort && field.name === this.sort.field && !this.sort.desc) {
                    return [...item[field.name]].reverse()
                }
			    if (!field.name) return item
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
            .array {
                height: 24px;
            }
        }
    }
</style>
