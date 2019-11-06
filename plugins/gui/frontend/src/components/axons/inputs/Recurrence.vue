<template>
  <div class="recurrence-grid">
    <div class="grid-row">
      <input
        id="period-daily"
        ref="periodDaily"
        v-model="value.period"
        type="radio"
        value="daily"
        :disabled="readOnly"
      >
      <label for="period-daily">Daily</label>
    </div>
    <div class="grid-row">
      <input
        id="period-weekly"
        v-model="value.period"
        type="radio"
        value="weekly"
        :disabled="readOnly"
      >
      <label for="period-weekly">Weekly</label>
      <div
        v-if="value.period === 'weekly'"
        class="send-day"
      >
        <label>on:</label>
        <x-select
          id="weekly-day"
          v-model="value.period_config.week_day"
          class="weekly-day"
          :options="weekDays"
        />
      </div>
    </div>
    <div class="grid-row">
      <input
        id="period-monthly"
        v-model="value.period"
        type="radio"
        value="monthly"
        :disabled="readOnly"
      >
      <label for="period-monthly">Monthly</label>
      <div
        v-if="value.period === 'monthly'"
        class="send-day"
      >
        <label>on day:</label>
        <x-select
          id="monthly-day"
          v-model="value.period_config.monthly_day"
          class="monthly-day"
          :options="monthDays"
        />
      </div>
    </div>
    <div class="grid-row send-hour-row">
      <div class="send-hour">
        <x-time-picker
          v-model="value.period_config.send_time"
          label="Send Email at:"
          :read-only="readOnly"
          @validate="validateSendTime"
        />
      </div>
      <label class="server-time">
        <svg-icon name="symbol/info" :original="true" height="16"/>
        Timezone is UTC
      </label>
    </div>
  </div>
</template>

<script>

    import xSelect from './Select.vue'
    import xTimePicker from './TimePicker.vue'
    import {weekDays, monthDays} from '../../../constants/utils'

    export default {
        name: "XRecurrence",
        components: {xSelect, xTimePicker },
        props: {
            value: {
                type: Object,
                default: () => {
                    return {
                        period: 'daily',
                        period_config: {
                            week_day: 0,
                            monthly_day: 1,
                            send_time: '13:00',
                        }
                    }
                },
            },
            readOnly: {
                type: Boolean, default: false
            }
        },
        data()  {
            return {
                weekDays: weekDays,
                monthDays: monthDays
            }
        },
        methods: {
            validateSendTime(valid){
                this.$emit('validate', valid)
            }
        }
    }
</script>

<style>
  .recurrence-grid{
    display: flex;
    flex-direction: column;
    grid-template-columns: 20px auto;
    grid-row-gap: 8px;
    align-items: center;

    .grid-row {
      display: flex;
      flex-direction: row;
      align-self: flex-start;
      width: 400px;
      line-height: 32px;

      label {
        margin-left: 0;
        flex: 1;
      }

      input[type="radio"] {
        margin: 9px 0.7ex;
      }

      .send-day{
        flex: 1;
        display: inline-flex;
        text-align: right;

        label {
          margin-right: 15px;
        }

        .weekly-day {
          width: 125px;
          padding-right: 20px;
          text-align: left;
        }

        .monthly-day {
          width: 125px;
          padding-right: 20px;
          text-align: left;
        }
      }

      &.send-hour-row {
        width: 600px;
        margin-top: 10px;

        .server-time {
          margin-left: 10px;
          line-height: 40px;
        }
      }
      .send-hour {
        .time-picker-text {
          display: flex;
          flex-direction: row;
          align-self: flex-end;
          width: 400px;

          label {
            text-align: right;
            margin-right: 15px;
          }
          .v-input  {
            width: 125px;
            flex: unset;
          }
          .v-text-field {
            padding-top: 0;
          }

          .error--text {
            .v-input__slot:before {
              border-color: $indicator-error
            }
            input[type="text"] {
              border-color: $indicator-error;
              border-width: 1px;
            }
          }

          .v-input__slot:before {
            border-color: rgba(0, 0, 0, 0);
          }
        }

      }

    }
  }

  .send-hour {
    line-height: 36px;
  }
</style>