<template>
  <x-page
    class="x-report"
    :breadcrumbs="[
      { title: 'reports', path: { name: 'Reports'}},
      { title: name }]"
  >
    <x-box>
      <div
        v-if="loading"
        class="v-spinner-bg"
      />
      <pulse-loader
        :loading="loading"
        color="#FF7D46"
      />
      <div class="page-content main">
        <div class="report-title">The report will be generated as a PDF file, every Discovery Cycle<span v-if="isLatestReport">, {{ last_generated }}</span></div>
        <div class="item">
          <label class="report-name-label">Report Name</label>
          <input
            v-if="id === 'new'"
            id="report_name"
            ref="name"
            v-model="report.name"
            :disabled="isReadOnly"
            class="report-name-textbox"
            @validate="onValidate"
          >
          <input
            v-else
            :value="report.name"
            disabled
            class="report-name-textbox"
          >
        </div>
        <h5 class="inner-title">Report Configuration</h5>
        <div>Select the data to include in the report</div>
        <div class="inner-content">
          <x-checkbox
            v-model="report.include_dashboard"
            value="IncludeDashboard"
            :read-only="readOnly"
            label="Include dashboard charts"
            class="item"
          />
          <x-checkbox
            v-model="report.include_saved_views"
            value="IncludeSavedViews"
            :read-only="readOnly"
            label="Include Saved Queries data"
            class="item"
            @change="validateSavedQueries"
          />
          <div
            v-if="report.include_saved_views"
            class="item"
          >
            <div class="saved-queries">
              <div
                v-for="(view,i) in report.views"
                :key="i"
              >
                <div class="saved-query">
                  <x-select-symbol
                    v-model="report.views[i].entity"
                    :options="entityOptions"
                    type="icon"
                    placeholder="mod"
                    :read-only="readOnly"
                    minimal
                    @input="onEntityChange($event, i)"
                  />
                  <x-select
                    v-model="report.views[i].name"
                    :options="viewOptions(i)"
                    searchable
                    placeholder="query name"
                    :read-only="readOnly"
                    class="query-name"
                    @input="onQueryNameChange($event, i)"
                  />
                  <x-button
                    link
                    class="query-remove"
                    @click="() => removeQuery(i)"
                  >x</x-button>
                </div>
              </div>
              <x-button
                light
                class="query-add"
                @click="addQuery"
              >+</x-button>
            </div>
          </div>
        </div>
        <div class="item">
          <div class="header">
            <x-checkbox
              id="report_schedule"
              v-model="report.add_scheduling"
              :read-only="readOnly"
              value="AddScheduling"
              @change="onAddScheduling"
            />
            <h5
              class="title"
              @click="toggleScheduling"
            >Email Configuration</h5>
            <div class="hint">Optional</div>
          </div>
          <div class="email-description">Scheduled Email with the report attached will be sent</div>
          <div class="inner-content schedule">
            <x-array-edit
              v-if="report.add_scheduling"
              v-model="report.mail_properties"
              :schema="mailSchema"
              :read-only="readOnly"
              @validate="onValidate"
              ref="mail_ref"
            />
            <div
              v-if="report.add_scheduling"
              id="report_scheduling"
            >
              <h4 class="title">Email Recurrence</h4>
              <div class="x-grid">
                <input
                  id="period-daily"
                  ref="periodDaily"
                  v-model="report.period"
                  type="radio"
                  value="daily"
                  :disabled="isReadOnly"
                >
                <label for="period-daily">Daily</label>
                <input
                  id="period-weekly"
                  v-model="report.period"
                  type="radio"
                  value="weekly"
                  :disabled="isReadOnly"
                >
                <label for="period-weekly">Weekly</label>
                <input
                  id="period-monthly"
                  v-model="report.period"
                  type="radio"
                  value="monthly"
                  :disabled="isReadOnly"
                >
                <label for="period-monthly">Monthly</label>
              </div>
            </div>
          </div>
        </div>

      </div>
      <div class="x-section x-btn-container footer">
        <div class="error-text">
          {{ error }}
        </div>
        <div>
          <x-button
            v-if="!hideTestNow"
            id="test-report"
            inverse
            @click="runNow"
          >Send Email</x-button>
          <x-button
            v-if="!hideDownloadNow"
            id="reports_download"
            inverse-emphasize
            :disabled="disableDownloadReport"
            @click="startDownload"
          >
            <template v-if="downloading">DOWNLOADING...</template>
            <template v-else>Download Report</template>
          </x-button>
          <x-button
            id="save-report"
            :disabled="!valid"
            @click="saveExit"
          >Save</x-button>
        </div>
      </div>
    </x-box>
    <x-toast
      v-if="message"
      :value="message"
      :timeout="toastTimeout"
      @done="removeToast"
    />
  </x-page>
</template>

<script>
  import Vue from 'vue'
  import xPage from '../axons/layout/Page.vue'
  import xBox from '../axons/layout/Box.vue'
  import xButton from '../axons/inputs/Button.vue'
  import xCheckbox from '../axons/inputs/Checkbox.vue'
  import xSelectSymbol from '../neurons/inputs/SelectSymbol.vue'
  import xSelect from '../axons/inputs/Select.vue'
  import viewsMixin from '../../mixins/views'
  import xArrayEdit from '../neurons/schema/types/array/ArrayEdit.vue'
  import xToast from '../axons/popover/Toast.vue'
  import configMixin from '../../mixins/config'
  import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'
  import {
    initRecipe, FETCH_REPORT, SAVE_REPORT, RUN_REPORT, DOWNLOAD_REPORT
  } from '../../store/modules/reports'

  export default {
    name: 'XReport',
    components: { xPage, xBox, xButton, xSelect, xCheckbox, xSelectSymbol, xArrayEdit, xToast, PulseLoader },
    mixins: [viewsMixin, configMixin],
    props: {
      readOnly: Boolean
    },
    data () {
      return {
        report: {
          include_dashboard: false,
          include_saved_views: false,
          views: [{ entity: '', name: '' }],
          recipients: [],
          add_scheduling: null,
          period: 'daily',
          mail_properties: {
            mailSubject: '',
            emailList: [],
            emailListCC: []
          }
        },
        downloading: false,
        queryValidity: false,
        scheduleValidity: false,
        toastTimeout: 50000,
        message: null,
        validity: {
          fields: [], error: ''
        },
        last_generated: null,
        isLatestReport: false,
        loading: false
      }
    },
    computed: {

      ...mapState({
        reportData (state) {
          return state.reports.current.data
        },
        reportFetching (state) {
          return state.reports.current.fetching
        },
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Reports === 'ReadOnly'
        },
        disableDownloadReport () {
          return this.downloading
        }
      }),
      id () {
        return this.$route.params.id
      },
      name () {
        if (!this.reportData || !this.reportData.name) return 'New Report'

        return this.reportData.name
      },
      disableSave () {
        return !this.report.name || !this.trigger || !this.trigger.view || !this.trigger.view.name || !this.mainAction.name
      },
      hideTestNow () {
        if (!this.valid) {
          return true
        }
        if (!this.report.add_scheduling) {
          return true
        }
        if (!this.report.last_generated) {
          return true
        }
        if (!this.validateEmail) {
          return true
        }
        return false
      },
      hideDownloadNow () {
        return !this.report.last_generated
      },
      valid () {
        if (this.isReadOnly) {
          return false
        }
        if (!this.report.name) {
          return false
        }
        if (!this.report.include_dashboard && !this.report.include_saved_views) {
          return false
        }
        if (this.report.include_saved_views) {
          if (!this.queryValidity) {
            return false
          }
        }
        if (this.report.add_scheduling) {
          if (this.validity.error) {
            return false
          }
        }
        return true
      },
      error () {
        if (!this.report.name) {
          return 'Report Name is a required field'
        }
        if (!this.report.include_dashboard && !this.report.include_saved_views) {
          return 'You must include the dashboard or "Saved Views"'
        }
        if (this.report.include_saved_views) {
          if (!this.queryValidity) {
            return 'The "Saved Queries" are invalid'
          }
        }
        if (this.report.add_scheduling) {
          return this.validity.error
        }
        return ''
      },
      mailSchema () {
        return {
          name: 'mail_config', title: '',
          items: [
            {
              'name': 'mailSubject',
              'title': 'Subject',
              'type': 'string',
              'required': true
            },
            {
              'name': 'emailList',
              'title': 'Recipients',
              'type': 'array',
              'items': {
                'type': 'string',
                'format': 'email'
              },
              'required': true
            },
            {
              'name': 'emailListCC',
              'title': 'Recipients CC',
              'type': 'array',
              'items': {
                'type': 'string',
                'format': 'email'
              }
            }
          ],
          'required': [
            'mailSubject', 'emailList'
          ],
          'type': 'array'
        }
      }
    },
    created () {
      if (!this.reportFetching && (!this.reportData.uuid || this.reportData.uuid !== this.id)) {
        this.loading = true
        this.fetchReport(this.id).then(() => {
          this.initData()
          this.loading = false
        })
      } else {
        this.initData()
      }
    },
    mounted () {
      if (this.$refs.name) {
        this.$refs.name.focus()
      }
    },
    methods: {
      ...mapMutations({
        tour: CHANGE_TOUR_STATE
      }),
      ...mapActions({
        fetchReport: FETCH_REPORT, saveReport: SAVE_REPORT,
        runReport: RUN_REPORT, downloadReport: DOWNLOAD_REPORT
      }),
      initData () {
        if (this.reportData && this.reportData.name) {
          this.report = this.reportData ? { ...this.reportData } : {}
          if (this.report.views.length == 0) {
            this.report.views.push({ entity: '', name: '' })
          }

          if (this.report.last_generated == null) {
            this.isLatestReport = false
          } else {
            let dateTime = new Date(this.report.last_generated)
            if (dateTime) {
              dateTime.setMinutes(dateTime.getMinutes() - dateTime.getTimezoneOffset())
              let dateParts = dateTime.toISOString().split('T')
              dateParts[1] = dateParts[1].split('.')[0]
              this.last_generated = 'Last generated: ' + dateParts.join(' ')
              this.isLatestReport = true
            } else {
              this.isLatestReport = false
            }
          }

        }
        this.validateSavedQueries()
      },
      startDownload () {
        if (this.disableDownloadReport) return
        this.downloading = true
        this.downloadReport(this.report.name).then((response) => {
          this.downloading = false
          this.tour({ name: 'tourFinale' })
        }).catch((error) => {
          this.downloading = false
          this.message = error.response.data.message
        })
      },
      onAddScheduling () {
        let actionName = this.settingToActions.mail[0]
        this.checkEmptySettings(actionName)
        if (this.anyEmptySettings) {
          this.report.add_scheduling = false
          return
        }
        setTimeout(() => {
          if (this.report.add_scheduling) {
            this.$refs.mail_ref.validate()
          }
        })

      },
      toggleScheduling () {
        this.report.add_scheduling = !this.report.add_scheduling
        this.onAddScheduling()
        setTimeout(() => {
          if (this.report.add_scheduling) {
            this.$refs.mail_ref.validate()
          }
        })
        this.$forceUpdate()
      },
      runNow () {
        let self = this
        this.saveReport(this.report).then(() => {
          setTimeout(() => {
            self.runReport(this.report).then(() => {
              this.message = 'Email is being sent'
              setTimeout(() => {
                self.message = 'Email sent successfully'
              })
            }).catch((error) => {
              this.message = error.response.data.message
            })
          }, 2000)
        })
      },
      saveExit () {
        this.message = 'Saving the report...'
        let self = this
        this.saveReport(this.report).then(
                () => {
                  self.exit()
                }
        ).catch((error) => {
          this.message = error.response.data
        })
      },
      exit () {
        this.$router.push({ name: 'Reports' })
      },
      onEntityChange (name, index) {
        Vue.set(this.report.views, index, { entity: name, name: '' })
        this.$forceUpdate()
        this.validateSavedQueries()
      },
      addQuery () {
        this.report.views.push({ entity: '', name: '' })
        this.$forceUpdate()
        this.validateSavedQueries()
      },
      removeQuery (index) {
        this.report.views.splice(index, 1)
        this.$forceUpdate()
        this.validateSavedQueries()

      },
      onQueryNameChange (name, index) {
        Vue.set(this.report.views, index, { entity: this.report.views[index].entity, name: name })
        this.$forceUpdate()
        this.validateSavedQueries()

      },
      viewOptions (index) {
        if (!this.views && !this.report.views[index].entity) return
        let views = (this.report.views && this.report.views[index]) ? this.views[this.report.views[index].entity] : []
        if (this.report.views && this.report.views > length > 0 && this.report.views[index].name && !views.some(view => view.name === this.report.views[index].name)) {
          views.push({
            name: this.report.view[index].name, title: `${this.report.views[0].name} (deleted)`
          })
        }
        return views
      },
      validateEmail () {
        if (this.report.mail_properties.mailSubject && this.report.mail_properties.emailList.length > 0) {
          return true
        }
        return false
      },
      validateSavedQueries () {
        let result = true
        if (!this.report.include_saved_views) {
          this.queryValidity = result
          return
        }
        if (this.report.views && this.report.views.length === 0) {
          result = false
        }
        this.report.views.forEach(view => {
          if (!view.entity || !view.name) {
            result = false
          }
        })
        this.queryValidity = result
      },
      removeToast () {
        this.message = ''
      },
      onValidate (field) {
        let validityChanged = false
        this.validity.fields = this.validity.fields.filter(x => x.name !== field.name)
        if (!field.valid) {
          this.validity.fields.push(field)
        }
        if (field.error) {
          if (!this.validity.error) {
            validityChanged = true
          }
          this.validity.error = field.error
        } else {
          let nextInvalidField = this.validity.fields.find(x => x.error)
          let nextResult = nextInvalidField ? nextInvalidField.error : ''
          if (nextResult != this.validity.error) {
            validityChanged = true
          }
          this.validity.error = nextResult
        }
        if (validityChanged) {
          this.$forceUpdate()
        }
      }
    }
  }
</script>

<style lang="scss">

    .x-box {
        overflow: hidden;
        height: 100%;
        padding-top: 12px;
    }
    .x-report {
        position: relative;
        .main {
            overflow: auto;
            max-height: calc(100% - 35px);
        }

        .page-content {
            height: 100%;
            line-height: 36px;

            .report-title {
                font-style: italic;
            }

            .inner-title {
                padding-top: 12px;
            }

            .inner-content {
                padding-top: 0px;
                padding-bottom: 0px;

            }

            .schedule {
                line-height: 20px;
            }

            .email-description {
                padding-left: 24px;
                padding-bottom: 12px;
            }

            .header {
                display: flex;
                align-items: center;
                margin-top: 24px;
                .x-checkbox {
                    margin-bottom: 4px;
                }
                .title {
                    margin: 0 0 0 8px;
                    cursor: pointer;
                }
            }

            .item {
                align-items: flex-end;
                width: 100%;
                display: inline-block;

                .report-name-label {
                    padding-right: 12px;
                }

                .report-name-textbox {
                    width: 200px;
                }

                .main {
                    margin-left: 24px;

                    .title {
                        margin: 24px 0 8px;
                    }
                }
            }
        }

        .error-text {
            height: 20px;
        }

        #reports_download {
            width: auto;
        }

        .x-grid {
            grid-template-columns: 20px auto;
            grid-row-gap: 8px;
            align-items: center;

            label {
                margin: 0;
            }
        }
        .save-queries-desc {
            padding-left: 24px;
            padding-bottom: 12px;
        }

        .saved-queries {
            display: grid;
            grid-template-columns: 1fr;
            grid-gap: 12px 24px;
            align-items: center;
            .saved-query {
                flex: 1 0 auto;
                margin-left: 24px;
                display: flex;
                .x-select-symbol {
                    width: 60px;
                    .content {
                      width: 120px;
                    }
                }
                .query-name {
                    flex: 1 0 auto;
                }
            }
            .md-switch {
                margin: 4px 0;
            }
        }

        .vm-select {
            width: 480px;

            .vm-select-input__inner {
                width: 100%;
            }
        }

        .x-btn-container {
            padding-top: 5px;
            text-align: right;

            .x-button {
                margin-left: 12px;
            }
        }

        .x-array-edit {
            display: grid;
            grid-template-columns: 1fr;
            grid-gap: 12px 24px;

            .object {
                width: 100%;

                input, select {
                    width: 100%;

                    &.error-border {
                        border-color: $indicator-error;
                    }
                }

                .error-border {
                    border: 1px solid $indicator-error;
                }
            }
        }
    }

    #report_schedule {
        margin-bottom: 0;
    }
</style>