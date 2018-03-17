<template>
    <div class="x-data-table">
        <div class="x-table-header">
            <div class="x-title">{{ title }} ({{count.data}})</div>
            <slot name="tableActions"/>
        </div>
        <pulse-loader :loading="loading" color="#FF7D46" />
        <div class="x-table-container">
            <table class="x-striped-table">
                <thead>
                    <tr class="x-row">
                        <th v-if="value">
                            <checkbox v-if="!loading" :data="value" :semi="value.length && value.length < ids.length"
                                      :value="ids" @change="$emit('input', $event)"/>
                        </th>
                        <th v-for="field in viewFields" nowrap>
                            <img v-if="field.logo" class="logo" :src="`/src/assets/images/logos/${field.logo}.png`"
                                 height="20">{{ field.title }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in pageData" @click="onClickRow(item[idField])" class="x-row clickable">
                        <td v-if="value">
                            <checkbox :data="value" :value="item[idField]" @change="$emit('input', $event)" />
                        </td>
                        <td v-for="field in viewFields" nowrap>
                            <component :is="`x-${field.type}-view`" :value="getData(item, field.name)" :schema="field"
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
	import { FETCH_DATA_CONTENT } from '../../store/actions'
    import { UPDATE_DATA_VIEW} from '../../store/mutations'
	import { mapState, mapMutations, mapActions } from 'vuex'

	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
	import Checkbox from '../inputs/Checkbox.vue'
	import xStringView from '../../components/controls/string/StringView.vue'
	import xNumberView from '../../components/controls/numerical/NumberView.vue'
	import xIntegerView from '../../components/controls/numerical/IntegerView.vue'
	import xBoolView from '../../components/controls/boolean/BooleanView.vue'
    import xFileView from '../../components/controls/array/FileView.vue'
	import xArrayView from '../../components/controls/array/ArrayInlineView.vue'
    import DataMixin from '../../mixins/data'

	export default {
		name: 'x-data-table',
        components: {PulseLoader, Checkbox, xStringView, xIntegerView, xNumberView, xBoolView, xFileView, xArrayView},
        mixins: [DataMixin],
        props: {module: {required: true}, fields: {required: true}, idField: {default: 'id'}, value: {}, title: {}},
        data() {
			return {
				loading: true
            }
        },
        computed: {
			...mapState({
                content(state) {
                	return state[this.module].data.content
                },
                count(state) {
                	return state[this.module].data.count
                },
                view(state) {
                	return state[this.module].data.view
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
            ...mapMutations({updateView: UPDATE_DATA_VIEW}),
			...mapActions({fetchContent: FETCH_DATA_CONTENT}),
            fetchLinkedPages() {
            	this.fetchContent({
					module: this.module, skip: this.pageLinkNumbers[0] * this.view.pageSize,
                    limit: this.pageLinkNumbers.length * this.view.pageSize
				})
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
        height: calc(100% - 40px);
        .x-table-header {
            display: flex;
            padding: 8px;
            line-height: 24px;
            .x-title {
                flex: 1 0 auto;
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
                        box-shadow: 0 2px 16px -4px $gray-dark;
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
                padding-top: 4px;
                .active, .x-link:hover {
                    cursor: pointer;
                    color: $orange;
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
                background: $white;
                border-bottom: 2px solid $white;
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
                    border-left: 20px solid $white;
                    border-radius: 2px;
                    left: -20px;
                    top: -20px;
                }
            }
        }
    }
</style>