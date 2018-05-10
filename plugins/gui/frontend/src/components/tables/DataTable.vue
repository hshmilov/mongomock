<template>
    <div class="x-data-table">
        <div class="x-table-header">
            <div class="x-title">{{ title }} ({{count.data}})</div>
            <div class="x-actions"><slot name="actions"/></div>
        </div>
        <div class="v-spinner-bg" v-if="loading"></div>
        <pulse-loader :loading="loading" color="#FF7D46" />
        <div class="x-table-container" :tabindex="-1" ref="greatTable">
            <table class="x-striped-table">
                <thead>
                    <tr class="x-row clickable">
                        <th v-if="value">
                            <x-checkbox v-if="!loading" :data="value" :semi="value.length && value.length < ids.length"
                                      :value="ids" @change="$emit('input', $event)" :tabindex="100"/>
                        </th>
                        <th v-for="field, i in viewFields" nowrap class="sortable" :tabindex="101 + i"
                            @click="onClickSort(field.name)" @keyup.enter.stop="onClickSort(field.name)">
                            <img v-if="field.logo" class="logo" :src="`/src/assets/images/logos/${field.logo}.png`"
                                 height="20">{{ field.title }}<div :class="`x-sort ${sortClass(field.name)}`"></div>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item, i in pageData" @click="onClickRow(item[idField])" class="x-row clickable">
                        <td v-if="value">
                            <x-checkbox :data="value" :value="item[idField]" @change="$emit('input', $event)"
                                        :tabindex="200 + i" />
                        </td>
                        <td v-for="field in viewFields" nowrap>
                            <component :is="`x-${field.type}-view`" :value="item[field.name]" :schema="field"
                                       :limit="2" :multiline="multiline"/>
                        </td>
                    </tr>
                <tr v-for="n in view.pageSize - pageData.length" class="x-row">
                    <td v-if="value">&nbsp;</td>
                    <td v-for="field in viewFields">&nbsp;</td>
                </tr>
                </tbody>
            </table>
        </div>
        <div class="x-pagination">
            <div class="x-sizes">
                <div class="x-title">results per page:</div>
                <div v-for="size, i in [20, 50, 100]" @click="onClickSize(size)" @keyup.enter="onClickSize(size)"
                     class="x-link" :class="{active: size === view.pageSize}" :tabindex="300 + i">{{size}}</div>
            </div>
            <div class="x-pages">
                <div @click="onClickPage(0)" @keyup.enter="onClickPage(0)"
                     :class="{'x-link': view.page > 0}" :tabindex="400">&lt;&lt;</div>
                <div @click="onClickPage(view.page - 1)" @keyup.enter="onClickPage(view.page - 1)"
                     :class="{'x-link': view.page - 1 >= 0}" :tabindex="401">&lt;</div>
                <div v-for="number in pageLinkNumbers" @click="onClickPage(number)" @keyup.enter="onClickPage(number)"
                     class="x-link" :class="{active: (number === view.page)}" :tabindex="402 + number">{{number + 1}}</div>
                <div @click="onClickPage(view.page + 1)" @keyup.enter="onClickPage(view.page + 1)"
                     :class="{'x-link': view.page + 1 <= pageCount}" :tabindex="450">&gt;</div>
                <div @click="onClickPage(pageCount)" @keyup.enter="onClickPage(pageCount)"
                     :class="{'x-link': view.page < pageCount}" :tabindex="451">&gt;&gt;</div>
            </div>
        </div>
    </div>
</template>

<script>
    import { GET_DATA_FIELD_LIST_SPREAD } from '../../store/getters'
	import { UPDATE_DATA_VIEW} from '../../store/mutations'
	import { FETCH_DATA_CONTENT } from '../../store/actions'
	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'

	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
	import xCheckbox from '../inputs/Checkbox.vue'
	import xStringView from '../../components/controls/string/StringView.vue'
	import xNumberView from '../../components/controls/numerical/NumberView.vue'
	import xIntegerView from '../../components/controls/numerical/IntegerView.vue'
	import xBoolView from '../../components/controls/boolean/BooleanView.vue'
    import xFileView from '../../components/controls/array/FileView.vue'
	import xArrayView from '../../components/controls/array/ArrayInlineView.vue'

	export default {
		name: 'x-data-table',
        components: {PulseLoader, xCheckbox, xStringView, xIntegerView, xNumberView, xBoolView, xFileView, xArrayView},
        props: {module: {required: true}, idField: {default: 'id'}, value: {}, title: {}},
        data() {
			return {
				loading: true
            }
        },
        computed: {
			...mapState({
                content(state) {
                	return state[this.module].content
                },
                count(state) {
                	return state[this.module].count
                },
                view(state) {
                	return state[this.module].view
                },
                refresh(state) {
                	if (!state['settings'] || !state['settings'].data || !state['settings'].data.refreshRate) return 0
                	return state['settings'].data.refreshRate
                },
                multiline(state) {
					if (!state['settings'] || !state['settings'].data || !state['settings'].data.multiLine) return false
					return state['settings'].data.multiLine
                }
			}),
            ...mapGetters({
                getDataFieldsListSpread: GET_DATA_FIELD_LIST_SPREAD
            }),
            fields() {
				return this.getDataFieldsListSpread(this.module)
            },
            viewFields() {
				return this.fields.filter((field) => field.name && this.view.fields.includes(field.name))
            },
            ids() {
				return this.content.data.map(item => item[this.idField])
            },
            pageData() {
				let pageId = 0
                this.pageLinkNumbers.forEach((number, index) => {
                	if (number === this.view.page) {
                		pageId = index
                    }
                })
				return this.content.data.slice(pageId * this.view.pageSize, (pageId + 1) * this.view.pageSize)
            },
            pageCount() {
				return Math.ceil(this.count.data / this.view.pageSize) - 1
            },
            pageLinkNumbers() {
                let numbers = []
                let steps = [5, 4, 3, 2, 1, 0]
                steps.forEach((step) => {
                	if (step > 2 && this.pageCount - this.view.page > 5 - step) return
                    if (this.view.page > step) {
                    	numbers.push(this.view.page - step - 1)
					}
                })
                numbers.push(this.view.page)
                steps.reverse().forEach((step) => {
					if (step > 2 && this.view.page > 5 - step) return
					if (this.pageCount - this.view.page > step) {
						numbers.push(this.view.page + step + 1)
					}
				})
                return numbers
            }
        },
        watch: {
            pageLinkNumbers() {
				this.fetchLinkedPages()
            },
            view(newView, oldView) {
            	if (newView.query.filter !== oldView.query.filter ||
                    Math.abs(newView.page - oldView.page) > 3) {
                    this.loading = true
                }
            }
        },
        methods: {
            ...mapMutations({updateView: UPDATE_DATA_VIEW}),
			...mapActions({fetchContent: FETCH_DATA_CONTENT}),
            fetchLinkedPages() {
            	this.fetchContent({
					module: this.module, skip: this.pageLinkNumbers[0] * this.view.pageSize,
                    limit: this.pageLinkNumbers.length * this.view.pageSize
				}).then(() => this.loading = false)
            },
            onClickRow(id) {
				if (!document.getSelection().isCollapsed) return
				this.$emit('click-row', id)
            },
            onClickSize(size) {
            	if (size === this.view.pageSize) return
                this.updateModuleView({ pageSize: size })
            },
            onClickPage(page) {
            	if (page === this.view.page) return
                if (page < 0 || page > this.pageCount) return
				this.updateModuleView({ page: page })
            },
            onClickSort(fieldName) {
            	let sort = { ...this.view.sort }
            	if (sort.field !== fieldName) {
            		sort.field = fieldName
                    sort.desc = true
                } else if (sort.desc) {
            		sort.desc = false
                } else {
            		sort.field = ''
                }
                this.updateModuleView({ sort, page: 0 })
            },
            sortClass(fieldName) {
            	if (this.view.sort.field !== fieldName) return ''
                if (this.view.sort.desc) return 'down'
				return 'up'
            },
            updateModuleView(view) {
            	this.updateView({module: this.module, view})
            }
        },
		created() {
			this.fetchLinkedPages()
            if (this.refresh) {
                this.interval = setInterval(function () {
					this.fetchLinkedPages()
                }.bind(this), this.refresh * 1000);
            }
		},
        mounted() {
			this.$refs.greatTable.focus()
        },
		beforeDestroy() {
			if (this.refresh && this.interval) {
			    clearInterval(this.interval);
            }
		}
	}
</script>

<style lang="scss">
    .x-data-table {
        height: calc(100% - 40px);
        .x-table-header {
            display: flex;
            padding: 8px;
            line-height: 24px;
            .x-title {
                flex: 1 0 auto;
            }
            .x-actions {
                display: grid;
                grid-auto-flow: column;
                grid-gap: 8px;
            }
        }
        .x-table-container {
            overflow: auto;
            max-height: calc(100% - 80px);
            .x-striped-table {
                .x-row {
                    height: 30px;
                    &.clickable:hover {
                        cursor: pointer;
                        box-shadow: 0 2px 16px -4px $grey-4;
                    }
                }
            }
            .item > div {
                display: inline;
            }
        }
        .x-pagination {
            justify-content: space-between;
            display: flex;
            .x-title {
                text-transform: uppercase;
            }
            .x-sizes {
                display: flex;
                width: 320px;
                justify-content: space-between;
                padding-top: 4px;
                .active, .x-link:hover {
                    cursor: pointer;
                    color: $theme-orange;
                    transition: color 0.4s;
                }
                .active:hover {
                    cursor: default;
                }
            }
            .x-pages {
                display: flex;
                width: 360px;
                min-height: 28px;
                justify-content: space-evenly;
                flex: 0 1 auto;
                position: relative;
                background: $theme-white;
                border-bottom: 2px solid $theme-white;
                border-radius: 2px;
                .active, .x-link:hover {
                    cursor: pointer;
                    font-weight: 500;
                    transition: font-weight 0.4s;
                }
                .active:hover {
                    cursor: default;
                }
                &:after {
                    content: '';
                    position: absolute;
                    transform: rotate(-45deg);
                    border: 20px solid transparent;
                    border-left: 20px solid $theme-white;
                    border-radius: 2px;
                    left: -20px;
                    top: -20px;
                }
            }
        }
    }
</style>