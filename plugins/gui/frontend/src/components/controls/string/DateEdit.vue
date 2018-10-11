<template>
    <date-picker :date="date" :option="dateTimeOption" @change="$emit('input', date.time)" :limit="limit" v-if="!disabled" />
    <input :value="value" :disabled="true" v-else>
</template>

<script>
    import DatePicker from 'vue-datepicker'

    export default {
        name: 'x-date-edit',
        components: { 'date-picker': DatePicker },
        props: {
            value: {
                required: false
            },
            limit: {
                required: false
            },
            showTime: {
                default: true
            },
            placeholder: {
                default: ''
            },
            disabled: {
                default: false
            }
        },
        computed: {
            dateTimeOption() {
                return {
                    type: this.showTime ? 'min' : 'day',
                    week: ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
                    month: ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'],
                    format: this.showTime ? 'YYYY-MM-DD HH:mm' : 'YYYY-MM-DD',
                    placeholder: this.placeholder,
                    inputStyle: {},
                    color: {
                        header: '#1d212c',
                        headerText: '#f26739'
                    }
                }
            }
        },
        data() {
            return {
                date: {time: this.value}
            }
        },
        watch: {
            value(newValue) {
                this.date.time = newValue
            }
        }
    }
</script>

<style lang="scss">
    .cov-vue-date {
        width: 100%;
        position: relative;
        .datepicker-overlay {
            position: relative !important;
            overflow: visible !important;
            .cov-date-body {
                position: absolute;
                transform: none;
                top: 0;
                left: 0;
                .cov-date-monthly, .cov-date-box, .button-box {
                    font-family: Roboto, sans-serif;
                    .hour-box, .min-box {
                        .hour-item, .min-item {
                            font-size: 20px !important;
                            &.active {
                                background-color: $grey-2;
                            }
                        }
                    }
                }
                .cov-date-monthly {
                    height: 48px;
                    padding: 4px;
                    .cov-date-caption {
                        padding: 0 !important;
                        height: 40px;
                        line-height: 40px;
                        vertical-align: middle;
                        direction: rtl;
                        width: 80%;
                        font-size: 18px;
                        br {
                            display: none;
                        }
                        span:last-child {
                            float: left;
                            margin-left: 20px;
                        }
                    }
                    .cov-date-previous, .cov-date-next {
                        height: 40px;
                        width: 10% !important;
                        &::before, &::after {
                            width: 10px;
                        }
                        &::after {
                            margin-top: 0;
                        }
                    }
                }
                .cov-date-box {
                    height: 240px;
                    .cov-picker-box {
                        padding: 0;
                        height: 240px;
                        .week {
                            background-color: $theme-black !important;
                            ul li {
                                color: $theme-white !important;
                                font-weight: 200 !important;
                            }
                        }
                        .day.checked {
                            background-color: $theme-orange !important;
                        }
                    }
                }
                .button-box {
                    padding: 0;
                    display: flex;
                    height: 40px;
                    border-top: 1px solid $grey-2;
                    span {
                        flex: 50%;
                        line-height: 20px;
                        text-align: center;
                        &:hover {
                            background-color: $grey-2;
                        }
                    }
                }
            }
        }
    }
</style>