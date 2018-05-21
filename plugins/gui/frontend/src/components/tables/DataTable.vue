<template>
    <div class="x-data-table" :class="{multiline: multiline}">
        <x-actionable-table :title="title" :count="count.data" :loading="loading">
            <slot name="actions" slot="actions"/>
            <x-table slot="table" :data="pageData" :fields="viewFields" :page-size="view.pageSize" :sort="view.sort"
                     :id-field="idField" :value="value" @input="$emit('input', $event)"
                     :click-row-handler="onClickRow" :click-col-handler="onClickSort"/>
        </x-actionable-table>
        <div class="x-pagination">
            <div class="x-sizes">
                <div class="x-title">results per page:</div>
                <div v-for="size, i in [20, 50, 100]" @click="onClickSize(size)" @keyup.enter="onClickSize(size)"
                     class="x-link" :class="{active: size === view.pageSize}">{{size}}</div>
            </div>
            <div class="x-pages">
                <div @click="onClickPage(0)" @keyup.enter="onClickPage(0)"
                     :class="{'x-link': view.page > 0}">&lt;&lt;</div>
                <div @click="onClickPage(view.page - 1)" @keyup.enter="onClickPage(view.page - 1)"
                     :class="{'x-link': view.page - 1 >= 0}">&lt;</div>
                <div v-for="number in pageLinkNumbers" @click="onClickPage(number)" @keyup.enter="onClickPage(number)"
                     class="x-link" :class="{active: (number === view.page)}">{{number + 1}}</div>
                <div @click="onClickPage(view.page + 1)" @keyup.enter="onClickPage(view.page + 1)"
                     :class="{'x-link': view.page + 1 <= pageCount}">&gt;</div>
                <div @click="onClickPage(pageCount)" @keyup.enter="onClickPage(pageCount)"
                     :class="{'x-link': view.page < pageCount}">&gt;&gt;</div>
            </div>
        </div>
    </div>
</template>

<script>
    import xActionableTable from './TableActions.vue'
	import xTable from './Table.vue'

    import { GET_DATA_FIELD_LIST_SPREAD } from '../../store/getters'
	import { UPDATE_DATA_VIEW} from '../../store/mutations'
	import { FETCH_DATA_CONTENT } from '../../store/actions'
	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'

	export default {
		name: 'x-data-table',
        components: { xActionableTable, xTable },
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
                	if (!state.configurable || !state.configurable.gui) return 0
                	return state.configurable.gui.GuiService.config.system_settings.refreshRate
                },
                multiline(state) {
                	if (!state.configurable || !state.configurable.gui) return 0
                	return state.configurable.gui.GuiService.config.system_settings.multiLine
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
                    Math.abs(newView.page - oldView.page) > 3 ||
                    newView.fields.length > oldView.fields.length) {
                    this.loading = true
                }
            }
        },
        methods: {
            ...mapMutations({updateView: UPDATE_DATA_VIEW}),
			...mapActions({fetchContent: FETCH_DATA_CONTENT}),
            fetchLinkedPages() {
            	return this.fetchContent({
					module: this.module, skip: this.pageLinkNumbers[0] * this.view.pageSize,
                    limit: this.pageLinkNumbers.length * this.view.pageSize
				}).then(() => {
					if (!this.content.fetching) {
					    this.loading = false
                    }
				})
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
            updateModuleView(view) {
            	this.updateView({module: this.module, view})
            }
        },
		created() {
			if (!this.pageData || !this.pageData.length) {
			    this.fetchLinkedPages()
            } else {
				this.loading = false
            }
            if (this.refresh) {
                const fetchAuto = () => {
					this.fetchLinkedPages().then(() => this.timer = setTimeout(fetchAuto, this.refresh * 1000))
                }
				this.timer = setTimeout(fetchAuto, this.refresh * 1000)
            }
		},
        beforeDestroy() {
			clearTimeout(this.timer)
        }
	}
</script>

<style lang="scss">
    .x-data-table {
        height: calc(100% - 40px);
        &.multiline .array {
            display: block;
            height: auto;
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