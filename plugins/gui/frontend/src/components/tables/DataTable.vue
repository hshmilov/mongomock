<template>
    <div class="x-data-table">
        <pulse-loader :loading="loading" color="#FF7D46" />
        <div class="x-data-table-container">
            <table class="x-striped-table">
                <thead>
                    <tr class="x-row">
                        <th v-if="value">
                            <checkbox v-if="!loading" :data="value" :semi="value.length && value.length < ids.length"
                                      :value="ids" @change="$emit('input', $event)"/>
                        </th>
                        <th v-for="field in viewFields" nowrap>
                            <img v-if="field.logo" :src="`/src/assets/images/logos/${field.logo}.png`">{{ field.title }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in pageData" @click="onClickRow(item[idField])" class="x-row clickable">
                        <td v-if="value">
                            <checkbox :data="value" :value="item[idField]" @change="$emit('input', $event)" />
                        </td>
                        <td v-for="field in viewFields" nowrap>
                            <component :is="`x-${field.type}-view`" :value="getData(item, field.name)" :schema="field"
                                       :limit="2"/>
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
                <div v-for="size in [20, 50, 100]" @click="onClickSize(size)" class="x-link"
                     :class="{active: size === view.pageSize}">{{size}}</div>
            </div>
            <div class="x-pages">
                <div @click="onClickPage(0)" :class="{'x-link': view.page > 0}">&lt;&lt;</div>
                <div @click="onClickPage(view.page - 1)" :class="{'x-link': view.page - 1 >= 0}">&lt;</div>
                <div v-for="number in pageLinkNumbers" @click="onClickPage(number)" class="x-link"
                     :class="{active: (number === view.page)}">{{number + 1}}</div>
                <div @click="onClickPage(view.page + 1)" :class="{'x-link': view.page + 1 <= pageCount}">&gt;</div>
                <div @click="onClickPage(pageCount)" :class="{'x-link': view.page < pageCount}">&gt;&gt;</div>
            </div>
        </div>
    </div>
</template>

<script>
	import { FETCH_TABLE_CONTENT } from '../../store/actions'
    import { UPDATE_TABLE_VIEW} from '../../store/mutations'
	import { mapState, mapMutations, mapActions } from 'vuex'

	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
	import Checkbox from '../inputs/Checkbox.vue'
	import xStringView from '../../components/controls/string/StringView.vue'
	import xNumberView from '../../components/controls/numerical/NumberView.vue'
	import xIntegerView from '../../components/controls/numerical/IntegerView.vue'
	import xBoolView from '../../components/controls/boolean/BooleanView.vue'
    import xFileView from '../../components/controls/array/FileView.vue'
	import xArrayView from '../../components/controls/array/ArrayInlineView.vue'

	export default {
		name: 'x-data-table',
        components: {PulseLoader, Checkbox, xStringView, xIntegerView, xNumberView, xBoolView, xFileView, xArrayView},
        props: {module: {required: true}, fields: {required: true}, idField: {default: 'id'}, value: {}},
        data() {
			return {
				loading: false
            }
        },
        computed: {
			...mapState({
                content(state) {
                	return state[this.module].dataTable.content
                },
                count(state) {
                	return state[this.module].dataTable.count
                },
                view(state) {
                	return state[this.module].dataTable.view
                },
                refresh(state) {
                	if (!state['settings'] || !state['settings'].data || !state['settings'].data.refreshRate) return 0
                	return state['settings'].data.refreshRate
                }
			}),
            fetching() {
				return (!this.fields.length || this.content.fetching || this.count.fetching)
                    && (!this.content.data.length && this.count.data > 0)
            },
            viewFields() {
				return this.fields.filter((field) => field.name && this.view.fields.includes(field.name))
            },
            ids() {
				return this.content.data.map(item => item[this.idField])
            },
            pageData() {
				return this.content.data.slice(this.view.page * this.view.pageSize,
                    (this.view.page + 1) * this.view.pageSize)
            },
            pageCount() {
				return Math.floor(this.count.data / this.view.pageSize)
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
			fetching(newFetching) {
                this.loading = newFetching
            },
            pageData(newPageData) {
				if (!newPageData.length && this.count.data) {
					this.loading = true
                    this.fetchLinkedPages()
				}
            },
            pageLinkNumbers() {
				this.fetchLinkedPages()
            }
        },
        methods: {
            ...mapMutations({updateView: UPDATE_TABLE_VIEW}),
			...mapActions({fetchContent: FETCH_TABLE_CONTENT}),
            fetchLinkedPages() {
            	this.fetchContent({
					module: this.module, skip: this.pageLinkNumbers[0] * this.view.pageSize,
                    limit: this.pageLinkNumbers.length * this.view.pageSize
				})
            },
			getData(data, path) {
				if (!data) return ''

				if (!Array.isArray(data)) {
					let firstDot = path.indexOf('.')
					if (firstDot === -1) return data[path]
					return this.getData(data[path.substring(0, firstDot)], path.substring(firstDot + 1))
				}
                if (data.length === 1) return this.getData(data[0], path)

                let children = []
                data.forEach((item) => {
                    let child = this.getData(item, path)
                    if (!child) return

                    let basicChildren = children.map((child) => this.getDataBasic(child))
                    if (Array.isArray(child)) {
                        children = children.concat(child.filter(
                            (childItem => !this.matchArrayPrefix(basicChildren, this.getDataBasic(childItem)))))
                    } else if (!this.matchArrayPrefix(basicChildren, this.getDataBasic(child))) {
                        children.push(child)
                    }
                })
                return Array.from(children)
			},
            getDataBasic(data) {
            	if (typeof data === 'string') return data.toLowerCase()
                return data
            },
            matchArrayPrefix(array, prefix) {
            	return array.some(item => (item.match(`^${prefix}`) !== null))
            },
            onClickRow(id) {
				if (!document.getSelection().isCollapsed) return
				this.$emit('click-row', id)
            },
            onClickSize(size) {
            	if (size === this.view.pageSize) return
                this.updateView({module: this.module, view: { pageSize: size }})
            },
            onClickPage(page) {
            	if (page === this.view.page) return
                if (page < 0 || page > this.pageCount) return
				this.updateView({module: this.module, view: { page: page }})
            }
        },
		created() {
			if (this.content.data.length) {
				this.loading = false
			} else {
				this.fetchContent({module: this.module, skip: 0, limit: this.view.pageSize})
            }
            if (this.refresh) {
                this.interval = setInterval(function () {
					this.fetchLinkedPages()
                }.bind(this), this.refresh * 1000);
            }
		},
		beforeDestroy() {
			if (this.refresh && this.interval) {
			    clearInterval(this.interval);
            }
		}
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .x-data-table {
        .x-data-table-container {
            overflow: auto;
            height: 62vh;
            border-bottom: 1px solid $gray-light;
            .x-striped-table {
                .x-row {
                    height: 30px;
                    &.clickable:hover {
                        cursor: pointer;
                        -webkit-box-shadow: 0px 2px 16px -4px $gray-dark;
                        -moz-box-shadow: 0px 2px 16px -4px $gray-dark;
                        box-shadow: 0px 2px 16px -4px $gray-dark;
                    }
                }
            }
        }
        .item > div {
            display: inline;
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
                .active, .x-link:hover {
                    cursor: pointer;
                    color: $orange;
                    -webkit-transition: color 0.4s;
                    -moz-transition: color 0.4s;
                    -ms-transition: color 0.4s;
                    -o-transition: color 0.4s;
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
                background: $gray-light;
                border-bottom: 2px solid $gray-light;
                -webkit-border-radius: 2px;
                -moz-border-radius: 2px;
                border-radius: 2px;
                .active, .x-link:hover {
                    cursor: pointer;
                    font-weight: 500;
                    -webkit-transition: font-weight 0.4s;
                    -moz-transition: font-weight 0.4s;
                    -ms-transition: font-weight 0.4s;
                    -o-transition: font-weight 0.4s;
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
                    border-left: 20px solid $gray-light;
                    border-radius: 2px;
                    left: -20px;
                    top: -20px;
                }
            }
        }
    }
</style>