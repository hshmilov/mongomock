<template>
    <div class="table-responsive">
        <div class="dataTables_wrapper">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th v-if="toggleOne !== undefined" class="table-head checkbox-container">
                            <checkbox v-if="toggleAll !== undefined" :clickHandler="toggleAll"
                                      v-model="allSelected"></checkbox>
                        </th>
                        <th :class="`table-head field_count_${fields.length}`"
                            v-for="field in fields">{{ field.name }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="table-row" v-bind:class="{ active: record.selected }"
                        v-for="record in data.slice(currentPage * pageSize, (currentPage + 1) * pageSize)">
                        <td v-if="toggleOne !== undefined" class="table-row-data">
                            <checkbox :clickHandler="toggleOne.bind(this, record['_id'])"
                                      v-model="record.selected"></checkbox>
                        </td>
                        <td class="table-row-data" v-for="field in fields">
                            <template v-if="field.type === undefined || !field.type || field.type=='text'">
                                <span>{{ record[field.name] || '&nbsp' }}</span>
                            </template>
                            <template v-else-if="field.type === 'list'">
                                <span v-for="item in record[field.name]">{{ item }}</span>
                            </template>
                            <template v-else-if="field.type === 'image-list'">
                                <image-list :data="record[field.name]" :limit="2"></image-list>
                            </template>
                        </td>
                    </tr>
                </tbody>
            </table>
            <div v-if="error" class="dataTables_info error-text">{{ error }}</div>
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
        components: { Checkbox, ImageList },
        props: [
          'fetching', 'data', 'error', 'fetchData', 'toggleOne', 'toggleAll', 'fields'
        ],
        computed: {
            firstPage() {
                return this.currentPage === 0
            },
            lastPage() {
                return this.maxPages > 0 && this.currentPage === this.maxPages
            },
            filterFields() {
                return this.fields.filter(function(field) {
                    return !field.default
                }).map(function(field) {
                    return [field.name || field.path, field.path]
                })
            }
        },
        data() {
            return {
                pageSize: 4,
                linkedPageCount: 5,
                currentPage: 0,
                fetchedPages: 0,
                maxPages: 0,
                linkedPageStart: 0,
                allSelected: false
            }
        },
        watch: {
            filterFields: function (newFields, oldFields) {
                if (newFields.length <= oldFields.length) { return }
                this.maxPages = 0
                this.fetchedPages = 0
            }
        },
        methods: {
            addData() {
                this.fetchData({
                    skip: this.fetchedPages * this.pageSize,
                    limit: this.pageSize,
                    fields: JSON.stringify(this.filterFields)
                })
                this.fetchedPages++
            },
            prevPage() {
                if (this.firstPage) { return }
                this.currentPage--
                if (this.currentPage < parseInt(this.linkedPageCount / 2) + 1 + this.linkedPageStart
                  && this.linkedPageStart > 0) {
                    this.linkedPageStart--
                }

            },
            nextPage() {
                /* If there are no more pages to show, return */
                if (this.lastPage) { return }
                this.currentPage++
                if (this.currentPage === parseInt(this.linkedPageCount / 2) + 1 + this.linkedPageStart
                  && this.linkedPageStart + this.linkedPageCount <= this.maxPages) {
                    this.linkedPageStart++
                }
            },
            selectPage(page) {
                this.currentPage = page
                this.linkedPageStart = Math.max(this.currentPage - parseInt(this.linkedPageCount / 2), 0)
                this.linkedPageStart = Math.min(this.linkedPageStart, this.maxPages - this.linkedPageCount + 1)
            }
        },
        mounted() {
            /* Get initial data for first page of the table */
            this.addData()
        },
        updated() {
            if (this.fetchedPages === 0 && this.maxPages === 0) {
                /* Get initial data for first page of the table */
                this.addData()
                return
            }
            if (this.maxPages !== 0 || !this.data.length) { return }

            let actualPages = parseInt(this.data.length / this.pageSize)
            if (actualPages < this.fetchedPages) {
                this.maxPages = actualPages
                if (this.data.length % this.pageSize == 0) { this.maxPages-- }
                if (actualPages < this.linkedPageCount) { this.linkedPageCount = actualPages + 1 }
            } else {
                /* Continue getting pages until linked amount is fulfilled, so user does not wait for it */
                this.addData()
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .dataTables_wrapper {
        padding-top: 10px;
        .dataTables_info {
            display: inline-block;
            font-size: 80%;
        }
        .dataTables_paginate {
            float: right;
            text-align: right;
            padding-top: 0.25em;
            .paginate_button {
                box-sizing: border-box;
                display: inline-block;
                min-width: 1.5em;
                padding: 0.25em 0.5em;
                text-align: center;
                text-decoration: none;
                cursor: pointer;
                *cursor: hand;
                border: 1px solid $border-color;
                text-transform: uppercase;
                font-size: 90%;
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
    .table {
        border-collapse: separate;
        border-spacing: 0;
        .table-head {
            border: 0;
            text-transform: capitalize;
            padding: 8px;
            font-weight: 400;
            color: $color-theme;
            &.checkbox-container {
                padding-left: 9px;
            }
            &.field_count_6 {  width: 16.6%;  }
            &.field_count_5 {  width: 20%;  }
            &.field_count_4 {  width: 25%;  }
            &.field_count_3 {  width: 33%;  }
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
        }
        .table-row:first-of-type:not(:hover):not(.active) .table-row-data {
            border-top: 1px solid $border-color;
        }
    }
</style>