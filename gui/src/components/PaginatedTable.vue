<template>
    <div class="table-responsive paginated-table">
        <div class="dataTables_wrapper">
            <table class="table table-striped">
                <thead>
                <tr>
                    <th class="table-head checkbox-container">
                        <checkbox v-if="value !== undefined" v-model="selectAllRecords"
                                  @change="updateSelectedAll()"></checkbox>
                    </th>
                    <th class="table-head" v-for="field in fields">{{ field.name }}</th>
                    <th class="table-head" v-if="actions !== undefined"></th>
                </tr>
                </thead>
                <tbody>
                <tr class="table-row" v-bind:class="{ active: recordSelection[record['id']] }"
                    v-for="record in data.slice(currentPage * pageSize, (currentPage + 1) * pageSize)">
                    <td class="table-row-data">
                        <checkbox v-if="value !== undefined" v-model="recordSelection[record['id']]"
                                  @change="updateSelected()"></checkbox>
                    </td>
                    <td class="table-row-data" v-for="field in fields">
                        <template v-if="field.type === undefined || !field.type || field.type=='text'">
                            <span>{{ record[field.path] || '&nbsp' }}</span>
                        </template>
                        <template v-else-if="field.type === 'tag-list'">
                            <div v-if="record[field.path]">
                                    <span v-if="record[field.path].length > 0"
                                          class="tag-list-item">{{ record[field.path][0] }}</span>
                                <span v-if="record[field.path].length > 1"
                                      class="tag-list-item">{{ record[field.path][1] }}</span>
                                <span v-if="record[field.path].length > 2"
                                      class="tag-list-item">{{ record[field.path][2] }}</span>
                                <span v-if="record[field.path].length > 3"
                                      class="tag-list-total"> ({{ record[field.path].length }} more)</span>
                            </div>
                        </template>
                        <template v-else-if="field.type === 'image-list'">
                            <image-list :data="record[field.path]" :limit="3"></image-list>
                        </template>
                    </td>
                    <td class="table-row-data table-row-actions" v-if="actions !== undefined">
                        <a v-for="action in actions" @click="action.handler($event, record['id'])">
                            <i :class="action.trigger"></i>
                        </a>
                    </td>
                </tr>
                <tr v-if="currentPage === maxPages && ((data.length % pageSize) > 0 || data.length === 0)"
                    v-for="n in pageSize - (data.length % pageSize)" class="table-row pad">
                    <td class="table-row-data">&nbsp</td>
                    <td v-for="field in fields" class="table-row-data">&nbsp</td>
                    <td class="table-row-data" v-if="actions !== undefined">&nbsp</td>
                </tr>
                </tbody>
            </table>
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
        </div>
    </div>
</template>

<script>
	import Checkbox from './Checkbox.vue'
	import ImageList from './ImageList.vue'

	export default {
		name: 'paginated-table',
		components: {Checkbox, ImageList},
		props: [
			'fetching', 'data', 'error', 'fetchData', 'actions', 'fields', 'filter', 'value'

		],
		computed: {
			pageSize () {
				if (this.$resize && this.$mq.above('height', 900)) { return 11 }
				if (this.$resize && this.$mq.above('height', 850)) { return 10 }
				if (this.$resize && this.$mq.above('height', 800)) { return 9 }
				if (this.$resize && this.$mq.above('height', 750)) { return 8 }
				if (this.$resize && this.$mq.above('height', 700)) { return 7 }
				if (this.$resize && this.$mq.above('height', 650)) { return 6 }
				if (this.$resize && this.$mq.above('height', 600)) { return 5 }
				if (this.$resize && this.$mq.above('height', 550)) { return 4 }
				if (this.$resize && this.$mq.above('height', 500)) { return 3 }
				return 1
			},
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
			}
		},
		data () {
			return {
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
			pageSize: function (newPageSize) {
				this.maxPages = parseInt(this.data.length / newPageSize)
				this.linkedPageCount = Math.min(5, this.maxPages + 1)
				this.selectPage(0)
			},
			filterFields: function (newFields, oldFields) {
				if (newFields.length <= oldFields.length) { return }
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
				if (diff === this.pageSize * 1000) {
					this.maxPages += 1000
					this.linkedPageCount = Math.min(this.maxPages, 5)
					/* Continue getting pages until linked amount is fulfilled, so user does not wait for it */
					this.addData()
				} else if (!this.fetching) {
                    this.maxPages += parseInt(diff / this.pageSize)
					if (diff === 0) {
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
					skip: this.fetchedPages * this.pageSize * 1000,
					limit: this.pageSize * 1000,
					fields: this.filterFields,
					filter: this.filter
				})
			},
			prevPage () {
				if (this.firstPage) { return }
				this.currentPage--
				if (this.currentPage < parseInt(this.linkedPageCount / 2) + 1 + this.linkedPageStart
					&& this.linkedPageStart > 0) {
					this.linkedPageStart--
				}

			},
			nextPage () {
				/* If there are no more pages to show, return */
				if (this.lastPage) { return }
				this.currentPage++
				if (this.currentPage === parseInt(this.linkedPageCount / 2) + 1 + this.linkedPageStart
					&& (this.linkedPageStart + this.linkedPageCount <= this.maxPages || this.maxPages === 0)) {
					this.linkedPageStart++
				}
			},
			selectPage (page) {
				this.currentPage = page
				this.linkedPageStart = Math.max(this.currentPage - parseInt(this.linkedPageCount / 2), 0)
				this.linkedPageStart = Math.min(this.linkedPageStart, this.maxPages + 1 - this.linkedPageCount)
			}
		},
		mounted () {
			/* Get initial data for first page of the table */
			if (!this.data || !this.data.length) {
				this.addData()
			}
		}
	}
</script>

<style lang="scss">
    @import '../assets/scss/config';

    .dataTables_wrapper {
        padding-top: 10px;
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
                    border: 1px solid $color-theme;
                    background-color: $color-theme;
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
        .table-head {
            border: 0;
            text-transform: capitalize;
            padding: 8px;
            font-weight: 400;
            color: $color-theme;
            vertical-align: middle;
            &.checkbox-container {
                padding-left: 9px;
            }
        }
        .table-row {
            &:nth-of-type(odd) {
                background-color: $background-color-highlight;
            }
            &:hover, &.active {
                .table-row-data {
                    border-top: 1px solid $color-theme;
                    border-bottom: 1px solid $color-theme;
                    background-color: $background-color-hover;
                    &:first-of-type {
                        border-left: 1px solid $color-theme;
                    }
                    &:last-of-type {
                        border-right: 1px solid $color-theme;
                    }
                }
                .table-row-actions a {
                    visibility: visible;
                }
            }
            .table-row-data {
                padding: 8px;
                border-bottom: 1px solid $border-color;
                &:first-of-type {
                    border-left: 1px solid $border-color;
                }
                &:last-of-type {
                    border-right: 1px solid $border-color;
                }
            }
            .table-row-actions {
                text-align: center;
                a {
                    visibility: hidden;
                    &:hover {
                        color: $color-theme;
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
        .table-row:first-of-type:not(:hover):not(.active) .table-row-data {
            border-top: 1px solid $border-color;
        }
    }

    .tag-list-item {
        border-radius: 4px;
        border: 1px solid $border-color;
        border-right: 0;
        padding: 2px;
        margin-right: 20px;
        position: relative;
        margin-top: 8px;
        &::after {
            content: '';
            position: absolute;
            border-radius: 4px;
            transform: rotate(45deg);
            border-right: 1px solid #dcd8d8;
            border-top: 1px solid #dcd8d8;
            height: 20px;
            width: 20px;
            top: 4px;
            right: -9px;
        }
    }

    .tag-list-total {
        font-size: 70%;
        text-transform: uppercase;
    }
</style>