<template>
    <div class="paginated-table dataTables_wrapper"> 
        <pulse-loader :loading="fetching && (!data || !data.length)" color="#26dad2"></pulse-loader>
        <div class="table table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th class="table-head checkbox-container" v-if="value">
                            <checkbox v-if="value !== undefined" v-model="selectAllRecords"
                                      @change="updateSelectedAll()"></checkbox>
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
                            <checkbox v-if="value !== undefined" v-model="recordSelection[record[idField]]"
                                      @change="updateSelected"></checkbox>
                        </td>
                        <generic-table-cell class="table-row-data" v-for="field,index in fields" :key="index"
                                            v-if="!field.hidden" :type="field.type" :value="record[field.path]">
                        </generic-table-cell>
                        <td class="table-row-data table-row-actions" v-if="actions !== undefined">
                            <a v-for="action in actions" class="table-row-action" @click="action.handler(record[idField])">
                                <i v-if="action.triggerFont" :class="action.triggerFont"></i>
                                <svg-icon :name="action.triggerIcon" height="24" width="24"
                                          :original="true" v-else></svg-icon>
                            </a>
                        </td>
                    </tr>
                    <tr v-if="currentPage === maxPages && ((data.length % pageSize) > 0 || data.length === 0)"
                        v-for="n in pageSize - (data.length % pageSize)" class="table-row pad">
                        <td class="table-row-data" v-if="value">&nbsp</td>
                        <td v-for="field in viewFields" class="table-row-data">&nbsp</td>
                        <td class="table-row-data" v-if="actions !== undefined">&nbsp</td>
                    </tr>
                </tbody>
            </table>
            <div class="clearfix"></div>
        </div>
        <div v-if="error" class="dataTables_info alert-error">Problem occured while fetching data: {{ error }}</div>
        <div class="dataTables_paginate paging_simple_numbers">
            <a @click="prevPage" class="paginate_button squash_button"
               :class="{ 'disabled': firstPage}">Previous</a>
            <span class="squash_button">
                <a v-for="n in linkedPageCount"
                   v-on:click="selectPage(n - 1 + linkedPageStart)" class="paginate_button"
                   :class="{ 'active': currentPage === n - 1 + linkedPageStart }">{{ n + linkedPageStart }}</a>
            </span>
            <a @click="nextPage" class="paginate_button"
               :class="{ 'disabled': lastPage}">Next</a>
        </div>
        <slot></slot>
    </div>
</template>

<script>
	import Checkbox from './Checkbox.vue'
    import GenericTableCell from './GenericTableCell.vue'
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
    import './icons'

	export default {
		name: 'paginated-table',
		components: { Checkbox, GenericTableCell, PulseLoader },
		props: {
			'fetching': {}, 'data': {}, 'error': {}, 'fetchData': {}, 'filter': {}, 'value': {},
            'actions': {}, 'fields': {}, 'idField': {default: 'id'}, 'selectedPage': {}
		},
		computed: {
			firstPage () {
				return this.currentPage === 0
			},
			lastPage () {
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
				if (newFields.length <= oldFields.length) { return }
				this.maxPages = 0
				this.fetchedPages = 0
				this.currentPage = 0
				this.linkedPageCount = 1
				this.linkedPageStart = 0
				this.addData()
			},
			filter: function (newFilter) {
				this.maxPages = 0
				this.fetchedPages = 0
				this.currentPage = 0
				this.linkedPageCount = 1
				this.linkedPageStart = 0
				this.addData()
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
				let _this = this
				let selectedRecords = Object.keys(this.recordSelection).filter(function (id) {
					return _this.recordSelection[id]
				})
				this.$emit('input', selectedRecords)
			},
			updateSelectedAll () {
				if (this.selectAllRecords) {
					let _this = this
					this.data.forEach(function (record) {
						_this.recordSelection[record['id']] = true
					})
				} else {
					this.recordSelection = {}
				}
				this.updateSelected()
			},
			addData () {
				this.fetchData({
					skip: this.fetchedPages * this.pageSize * 50,
					limit: this.pageSize * 50,
					fields: this.filterFields,
					filter: this.filter
				})
			},
			prevPage () {
				if (this.firstPage) { return }
				this.selectPage(this.currentPage - 1)
			},
			nextPage () {
				/* If there are no more pages to show, return */
				if (this.lastPage) { return }
				this.selectPage(this.currentPage + 1)
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
			/* Get initial data for first page of the table */
			if (!this.data || !this.data.length) {
				this.addData()
			} else {
				/* Recalculating the pagination parameters, according to data */
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
    @import '../scss/config';

    .dataTables_wrapper {
        overflow-x: hidden;
        padding: 12px;
        .dataTables_info {
            display: inline-block;
            font-size: 80%;
        }
        .dataTables_paginate {
            float: right;
            text-align: right;
            .paginate_button {
                box-sizing: border-box;
                display: inline-block;
                min-width: 1.5em;
                text-align: center;
                text-decoration: none;
                cursor: pointer;
                *cursor: hand;
                border: 1px solid $border-color;
                text-transform: uppercase;
                font-size: 80%;
                padding: 8px 12px;
                &.active,
                &:hover {
                    color: $color-light;
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
            .squash_button {
                margin-right: -5px;
            }
        }
    }

    .paginated-table .table {
        border-collapse: separate;
        border-spacing: 0;
        overflow-x: auto;
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

</style>