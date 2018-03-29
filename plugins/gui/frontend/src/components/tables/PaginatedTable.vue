<template>
    <div class="paginated-table">
        <pulse-loader :loading="(fetching && !data.length) || !fields.length" color="#26dad2"/>
        <div class="table-container">
            <table class="table table-responsive">
                <thead>
                    <tr>
                        <th class="table-head checkbox-container" v-if="value">
                            <checkbox v-if="value !== undefined" v-model="selectAllRecords" @change="updateSelectedAll()"/>
                        </th>
                        <th class="table-head" v-for="field in fields" v-if="!field.hidden">{{ field.name }}</th>
                        <th class="table-head" v-if="actions !== undefined"></th>
                    </tr>
                </thead>
                <tbody>
                    <!-- idField should represent which field to take as id for each record.
                        This id is used for passing to action methods or marking the row as active -->
                    <tr class="table-row" v-bind:class="{ active: recordSelection[record[idField]] }"
                        v-for="record in data.slice(currentPage * pageSize, (currentPage + 1) * pageSize)"
                        @click="handleRowClick(record[idField])">
                        <td class="table-row-data" v-if="value">
                            <checkbox v-if="value !== undefined" v-model="recordSelection[record[idField]]" @change="updateSelected"/>
                        </td>
                        <generic-table-cell class="table-row-data" v-for="field,index in fields" :key="index"
                                            v-if="!field.hidden" :type="field.type" :value="record[field.path]">
                        </generic-table-cell>
                        <td class="table-row-data table-row-actions" v-if="actions !== undefined">
                            <a v-for="action in actions" class="table-row-action" @click="action.handler(record[idField])">
                                <i v-if="action.triggerFont" :class="action.triggerFont"></i>
                                <svg-icon :name="action.triggerIcon" height="24" width="24" :original="true" v-else></svg-icon>
                            </a>
                        </td>
                    </tr>
                    <tr v-if="currentPage === maxPages && ((data.length % pageSize) > 0 || data.length === 0)"
                        v-for="n in pageSize - (data.length % pageSize)" class="table-row pad">
                        <td class="table-row-data" v-if="value">&nbsp;</td>
                        <td v-for="field in viewFields" class="table-row-data">&nbsp;</td>
                        <td class="table-row-data" v-if="actions !== undefined">&nbsp;</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div v-if="error" class="info alert-error">Problem occured while fetching data: {{ error }}</div>
        <div class="pagination">
            <a @click="firstPage" class="btn" :class="{ 'disabled': isFirstPage}">&lt;&lt;</a>
            <a @click="prevPage" class="btn" :class="{ 'disabled': isFirstPage}">&lt;</a>
            <a v-for="n in linkedPageCount" v-on:click="selectPage(n - 1 + linkedPageStart)" class="btn"
               :class="{ 'active': currentPage === n - 1 + linkedPageStart }">{{ n + linkedPageStart }}</a>
            <a @click="nextPage" class="btn" :class="{ 'disabled': isLastPage}">&gt;</a>
            <a @click="lastPage" class="btn" :class="{ 'disabled': isLastPage}">&gt;&gt;</a>
        </div>
        <slot></slot>
    </div>
</template>

<script>
	import Checkbox from '../Checkbox.vue'
    import GenericTableCell from '../tables/GenericTableCell.vue'
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
    import '../icons'
	import xStringView from '../../components/controls/string/StringView.vue'
	import xNumberView from '../../components/controls/numerical/NumberView.vue'
	import xIntegerView from '../../components/controls/numerical/IntegerView.vue'
	import xBoolView from '../../components/controls/boolean/BooleanView.vue'
	import xFileView from '../../components/controls/array/FileView.vue'
    import xArrayView from '../../components/controls/array/ArrayView.vue'

	export default {
		name: 'paginated-table',
		components: { Checkbox, GenericTableCell, PulseLoader,
            xStringView, xNumberView, xIntegerView, xBoolView, xFileView, xArrayView},
		props: {
			'fetching': {}, 'data': {}, 'error': {}, 'fetchData': {}, 'filter': {}, 'value': {},
            'actions': {}, 'fields': {}, 'idField': {default: 'id'}, 'selectedPage': {}
		},
		computed: {
			isFirstPage () {
				return this.currentPage === 0
			},
			isLastPage () {
				return this.currentPage === this.maxPages
			},
			filterFields () {
				return this.fields.filter(function (field) {
					return !field.default
				}).map(function (field) {
					return field.path
				})
			},
            viewFields() {
				return this.fields.filter(function (field) {
					return !field.hidden
                })
            }
		},
		data () {
			return {
				pageSize: 10,
				linkedPageCount: 1,
				linkedPageStart: 0,
				currentPage: 0,
				fetchedPages: 0,
				maxPages: 0,
				selectAllRecords: false,
				recordSelection: {}
			}
		},
		watch: {
			filterFields: function (newFields, oldFields) {
				if (!oldFields.length || newFields.length <= oldFields.length) { return }
				this.restartData()
			},
			filter: function (newFilter) {
				this.restartData()
			},
			fetching: function (newFetching) {
				if (newFetching) {
					this.fetchedPages++
				}
			},
			data: function (newData, oldData) {
				let diff = newData.length - oldData.length
				if (diff === this.pageSize * 50) {
					this.maxPages += 50
					this.linkedPageCount = Math.min(this.maxPages, 5)
					/* Continue getting pages until linked amount is fulfilled, so user does not wait for it */
					this.addData()
				} else if (!this.fetching) {
                    this.maxPages += parseInt(diff / this.pageSize)
					if (diff % this.pageSize === 0 && this.maxPages > 0) {
						this.maxPages--
					}
					this.linkedPageCount = Math.min(5, this.maxPages + 1)
				}
			}
		},
		methods: {
			updateSelected () {
				let selectedRecords = Object.keys(this.recordSelection).filter((id) => {
					return this.recordSelection[id]
				})
				this.$emit('input', selectedRecords)
			},
			updateSelectedAll () {
				if (this.selectAllRecords) {
					this.data.forEach((record) => {
						this.recordSelection[record['id']] = true
					})
				} else {
					this.recordSelection = {}
				}
				this.updateSelected()
			},
			addData () {
				if (this.fetching) { return }
				this.fetchData({
					skip: this.fetchedPages * this.pageSize * 50,
					limit: this.pageSize * 50,
					fields: this.filterFields,
					filter: this.filter
				})
			},
            firstPage() {
				if (this.isFirstPage) { return }
				this.selectPage(0)
            },
			prevPage () {
				if (this.isFirstPage) { return }
				this.selectPage(this.currentPage - 1)
			},
			nextPage () {
				/* If there are no more pages to show, return */
				if (this.isLastPage) { return }
				this.selectPage(this.currentPage + 1)
			},
            lastPage() {
				if (this.isLastPage) { return }
				this.selectPage(this.maxPages)
            },
            restartData() {
				this.maxPages = 0
				this.fetchedPages = 0
				this.currentPage = 0
				this.linkedPageCount = 1
				this.linkedPageStart = 0
				this.recordSelection = {}
				this.addData()
            },
            restartPagination() {
				/*
				    Find first link to specific page, according to currently selected page.
				    This should beg half the total number of links before current page (first calculation),
				    unless total pages number will be passed this way (second calculation).
				*/
				this.linkedPageStart = Math.max(this.currentPage - parseInt(this.linkedPageCount / 2), 0)
				this.linkedPageStart = Math.min(this.linkedPageStart, this.maxPages + 1 - this.linkedPageCount)
            },
			selectPage (page) {
				this.currentPage = page
                this.$emit('change-page', page)
				this.restartPagination()
			},
            handleRowClick(id) {
				if (!document.getSelection().isCollapsed) {
					return
                }
				this.$emit('click-row', id)
            }
		},
		mounted () {
			if (this.selectedPage) {
			    this.currentPage = this.selectedPage
            }
			/* Get initial controls for first page of the table */
			if (!this.data || !this.data.length) {
				this.addData()
			} else {
				/* Recalculating the pagination parameters, according to controls */
				/* Max is zero-index (so needs to be rounded down) */
				this.maxPages = parseInt(this.data.length / this.pageSize)
                this.fetchedPages = this.maxPages
				this.linkedPageCount = Math.min(5, this.maxPages + 1)
				this.restartPagination()
            }
		}
	}
</script>

<style lang="scss">
    .paginated-table {
        .table-container {
            max-height: calc(100% - 40px);
        }
        .table {
            border-collapse: separate;
            border-spacing: 0;
            font-size: 14px;
            .table-head {
                border: 0;
                text-transform: capitalize;
                padding: 8px;
                font-weight: 400;
                color: $color-text-main;
                vertical-align: middle;
                &.checkbox-container {
                    padding-left: 9px;
                }
            }
            .table-row {
                cursor: pointer;
                &:hover, &.active {
                    .table-row-data {
                        background-color: $background-color-hover;
                    }
                    .table-row-actions a {
                        visibility: visible;
                        .svg-stroke {  stroke: $color-text-title;  }
                        .svg-fill {  fill: $color-text-title;  }
                    }
                }
                &:first-of-type .table-row-data {
                    border-top: 1px solid $border-color;
                }
                .table-row-data {
                    padding: 8px;
                    max-width: 120px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    border-top: 0;
                    border-bottom: 1px solid $border-color;
                    &:first-of-type {
                        border-left: 1px solid $border-color;
                    }
                    &:last-of-type {
                        border-right: 1px solid $border-color;
                    }
                }
                .table-row-actions {
                    text-align: right;
                    vertical-align: middle;
                    .table-row-action {
                        visibility: hidden;
                        padding-right: 20px;
                        &:hover {
                            color: $color-theme-light;
                            .svg-stroke {  stroke: $color-theme-light;  }
                            .svg-fill {  fill: $color-theme-light;  }
                        }
                        i {
                            vertical-align: middle;
                            font-size: 120%;
                        }
                    }
                }
                &.pad {
                    background-color: $background-color-light;
                    border: 0;
                    line-height: 28px;
                    .table-row-data {
                        border: 0;
                    }
                    &:hover, &.active {
                        .table-row-data {
                            background-color: $background-color-light;
                            border: 0;
                        }
                    }
                }
            }
            .table-row:last-of-type:not(:hover):not(.active) .table-row-data {
                border-bottom: 1px solid $border-color;
            }
        }
        .info {
            display: inline-block;
            font-size: 80%;
        }
        .pagination {
            justify-content: flex-end;
            margin-top: 8px;
            .btn {
                box-sizing: border-box;
                display: inline-block;
                width: auto;
                text-align: center;
                text-decoration: none;
                cursor: pointer;
                *cursor: hand;
                border: 1px solid $border-color;
                background-color: $background-color-light;
                text-transform: uppercase;
                font-size: 80%;
                padding: 8px 12px;
                height: auto;
                line-height: initial;
                &:not([href]):not([tabindex]) {
                    color: $color-text-main;
                }
                &.active,
                &:hover {
                    &:not([href]):not([tabindex]) {
                        color: $color-light;
                    }
                    border: 1px solid $color-theme-light;
                    background-color: $color-theme-light;
                }
                &.disabled,
                &.disabled:hover {
                    border: 1px solid $border-color;
                    cursor: default;
                    color: $color-disabled;
                    background: transparent;
                    box-shadow: none;
                }
            }
        }
    }

</style>