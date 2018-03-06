<template>
    <date-picker :date="date" :option="dateTimeOption" @change="$emit('input', date.time)" :limit="limit"></date-picker>
</template>

<script>
	import DatePicker from 'vue-datepicker'

	export default {
		name: 'x-date-edit',
		components: { 'date-picker': DatePicker },
        props: ['value', 'limit'],
        computed: {
			dateTimeOption() {
				return {
					type: 'min',
					week: ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
					month: ['January', 'February', 'March', 'April', 'May', 'June',
						'July', 'August', 'September', 'October', 'November', 'December'],
					format: (navigator.language === 'en-US') ? 'MM/DD/YYYY h:mm A' : 'DD/MM/YYYY HH:mm',
					placeholder: '',
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
				date: { time: this.value }
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
    @import '../../../scss/config';

    .cov-vue-date {
        width: 100%;
        position: relative;
        .datepicker-overlay {
            position: relative !important;
            overflow: visible !important;
            .cov-date-body {
                position: absolute;
                -webkit-transform: none;
                -moz-transform: none;
                -ms-transform: none;
                -o-transform: none;
                transform: none;
                top: 0;
                left: 0;
                .cov-date-monthly, .cov-date-box, .button-box {
                    font-family: Poppins, sans-serif;
                    .hour-box, .min-box {
                        .hour-item, .min-item {
                            font-size: 20px !important;
                            &.active {
                                background-color: $color-theme-light;
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
                        br { display: none; }
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
                    height: 200px;
                    .cov-picker-box {
                        padding: 0;
                        height: 200px;
                        overflow: hidden;
                        .week {
                            background-color: $color-theme-dark !important;
                            ul li {
                                color: $color-theme-light !important;
                                font-weight: 200 !important;
                            }
                        }
                        .day.checked {
                            background-color: $color-theme-light !important;
                        }
                    }
                }
                .button-box {
                    padding: 0;
                    display: flex;
                    height: 40px;
                    span {
                        flex: 50%;
                        line-height: 20px;
                        text-align: center;
                        &:hover {
                            background-color: #E3E3E3;
                        }
                    }
                }
            }
        }
    }
</style>