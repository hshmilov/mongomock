<template>
    <div class="week">
        <div @click="decCurrentWeek" class="x-btn link">&lt;</div>
        <div v-for="day in currentWeekDays" class="day">
            <div class="day-title">
                <div>{{day.date.format('ddd')}}</div>
                <div>{{day.date.toDate().toLocaleDateString()}}</div>
            </div>
            <div class="day-body">
                <div v-for="dose, index in day.instance_details" class="dose">
                    <div v-if="index" class="dose-link"></div>
                    <div v-if="dose.instance_state === 'Taken'" class="dose-percent"
                         :class="{success: dose.percentage_of_volume_infused === 1}">
                        <div :style="{height: dose.percentage_of_volume_infused * 100 + '%'}" class="dose-fill"></div>
                    </div>
                    <div v-else-if="dose.instance_state === 'Upcoming'" class="dose-placeholder"></div>
                    <div v-else-if="dose.instance_state === 'Missed'" class="dose-error"><x-cross /></div>
                </div>
            </div>
        </div>
        <div @click="incCurrentWeek" class="x-btn link">&gt;</div>
    </div>
</template>

<script>
    import xCross from '../patterns/Cross.vue'
    import moment from 'moment'

	export default {
		name: 'x-schema-calendar',
        components: { xCross },
        props: { data: { required: true }, schema: { required: true } },
        computed: {
			dataWeeks() {
				return Object.keys(this.data)
            },
            currentDays() {
            	/* List of dates to present, according to currently selected week */
                let days = []
                for (let i = 0; i < 7; i++) {
            		// Create each consecutive date, in the range of 7 days
                    days.push(this.currentWeekStart.clone().add(i, 'days'))
                }
                return days
            },
            currentDate() {
            	/* Create date object from current year and week */
            	return moment().year(this.currentYear).isoWeek(this.currentWeek)
            },
            currentWeekStart() {
				/* Find the date of the Monday, for the given week of given year */
				return this.currentDate.clone().startOf('isoWeek')
            },
            currentWeekData() {
				return this.data[`${this.currentYear}_${this.currentWeek}`]
            },
            currentWeekDays() {
				let dataIndex = 0
                return this.currentDays.map(day => {
                	/* Check for data of this day or just return the day, if none found */
                	if (!this.currentWeekData || dataIndex === this.currentWeekData.length
                        || !moment(this.currentWeekData[dataIndex].date).isSame(day, 'day')) {
                		// No data received for this day so return the date only
                        return { date: day }
                    }
                    // Found data matching current date, proceed to next one and return the current
                    dataIndex++
                    return { ...this.currentWeekData[dataIndex - 1], date: day }
                })
            }
        },
        data() {
			return {
				currentWeek: moment().isoWeek(),
                currentYear: moment().year()
            }
        },
        methods: {
            incCurrentWeek() {
                let nextWeek = this.currentDate.clone()
                nextWeek.add(1, 'weeks')
                this.currentWeek = nextWeek.isoWeek()
                this.currentYear = nextWeek.year()
            },
            decCurrentWeek() {
				let prevWeek = this.currentDate.clone()
                prevWeek.subtract(1, 'weeks')
				this.currentWeek = prevWeek.isoWeek()
				this.currentYear = prevWeek.year()
            }
        },
        created() {
			if (this.currentWeekData) return

			let minDateDiff = Infinity
            // Find week in data closest to current
            this.dataWeeks.forEach(week => {
				let weekParts = week.split('_').map(part => parseInt(part))
				let currentDateDiff = this.currentDate.diff(moment().year(weekParts[0]).isoWeek(weekParts[1]))
                if (currentDateDiff < minDateDiff) {
					// Current diff is smaller so current date is closer than previous
            		minDateDiff = currentDateDiff
					this.currentYear = weekParts[0]
					this.currentWeek = weekParts[1]
                }
            })
        }
	}
</script>

<style lang="scss">
    .week {
        height: 100%;
        display: grid;
        grid-template-columns: 1fr repeat(7, 4fr) 1fr;
        .x-btn.link {
            padding: 0 8px;
            font-size: 24px;
        }
        .day {
            display: flex;
            flex-direction: column;
            .day-title {
                font-weight: 400;
                color: $grey-4;
                text-align: center;
                border-bottom: 1px solid $theme-orange;
            }
            .day-body {
                border-right: 2px solid $grey-2;
                flex: 1 0 auto;
                padding: 12px;
                .dose {
                    .dose-link {
                        height: 24px;
                        width: 12px;
                        background-color: $grey-2;
                        margin: auto;
                    }
                    .dose-percent {
                        height: 36px;
                        width: 36px;
                        border: 1px solid $indicator-warning;
                        border-radius: 4px;
                        margin: auto;
                        display: flex;
                        align-items: flex-end;
                        .dose-fill {
                            background-color: $indicator-warning;
                            flex: auto;
                        }
                        &.success {
                            border: 1px solid $indicator-success;
                            .dose-fill {
                                background-color: $indicator-success;
                            }

                        }
                    }
                    .dose-placeholder {
                        height: 36px;
                        width: 36px;
                        border: 1px dashed $grey-3;
                        border-radius: 4px;
                        margin: auto;
                    }
                    .dose-error {
                        height: 36px;
                        width: 36px;
                        border: 1px solid $indicator-error;
                        border-radius: 4px;
                        margin: auto;
                        .cross {
                            height: 100%;
                            .top, .bottom {
                                margin: auto;
                            }
                            .top {
                                margin-bottom: 0;
                            }
                            .bottom {
                                margin-top: 2px;
                            }
                        }
                    }
                }
            }
            &:nth-child(2) .day-body {
                border-left: 2px solid $grey-2;
            }
        }
    }
</style>