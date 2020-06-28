<template>
  <XPage
    class="x-report"
    :breadcrumbs="[
      { title: 'reports', path: { name: 'Reports'}},
      { title: name }]"
  >
    <XBox>
      <div
        v-if="loading"
        class="v-spinner-bg"
      />
      <PulseLoader
        :loading="loading"
        color="#FF7D46"
      />
      <div class="page-content main">
        <div class="report-title">
          The report will be generated as a PDF file, every Discovery Cycle
          <span
            v-if="isLatestReport"
            :title="lastGeneratedTitle"
          >, {{ lastGenerated }}</span>
        </div>
        <div class="item">
          <label class="report-name-label">Report name</label>
          <input
            v-if="id === 'new'"
            id="report_name"
            ref="name"
            v-model="report.name"
            type="text"
            :disabled="cannotEditReport"
            class="report-name-textbox"
            @keyup="onNameChanged"
          >
          <input
            v-else
            type="text"
            :value="report.name"
            disabled
            class="report-name-textbox"
          >
        </div>
        <h5 class="inner-title">
          Report Configuration
        </h5>
        <div>Select the data to include in the report</div>
        <div class="inner-content">
          <XCheckbox
            v-model="report.include_dashboard"
            value="IncludeDashboard"
            :read-only="cannotEditReport || !canViewDashboard"
            label="Include dashboard charts"
            class="item"
          />
          <div
            v-if="canViewDashboard && report.include_dashboard"
            class="dashboard-spaces"
          >
            <XArrayEdit
              ref="spaces_ref"
              v-model="report.spaces"
              :schema="spacesSchema"
              :read-only="cannotEditReport"
              placeholder="Select spaces (or empty for all)"
            />
          </div>
          <XCheckbox
            v-model="report.include_saved_views"
            value="IncludeSavedViews"
            :read-only="cannotEditReport"
            label="Include Saved Queries data"
            class="item"
            @change="validateSavedQueries"
          />
          <div
            v-if="report.include_saved_views"
            class="item"
          >
            <div class="saved-queries">
              <XCheckbox
                v-if="report.add_scheduling"
                v-model="report.send_csv_attachments"
                value="IncludeCsv"
                :read-only="cannotEditReport"
                label=" Attach CSV with queries results to email"
                class="item"
              />
              <div
                v-for="(view, i) in report.views"
                :key="i"
              >
                <div class="saved-query">
                  <XSelectSymbol
                    v-model="report.views[i].entity"
                    :options="entityOptions"
                    type="icon"
                    placeholder="mod"
                    :read-only="!canEditSavedView(i)"
                    minimal
                    @input="onEntityChange($event, i)"
                  />
                  <XSelect
                    v-model="report.views[i].id"
                    :options="currentViewOptions(i)"
                    searchable
                    placeholder="query name"
                    :read-only="!canEditSavedView(i)"
                    class="query-name"
                    @input="onQueryNameChange($event, i)"
                  />
                  <XButton
                    type="link"
                    class="query-remove"
                    :disabled="cannotEditReport"
                    @click="() => removeQuery(i)"
                  >x</XButton>
                </div>
              </div>
              <XButton
                type="light"
                class="query-add"
                :disabled="cannotEditReport || entityOptions.length === 0"
                @click="addQuery"
              >+</XButton>
            </div>
          </div>
        </div>
        <div class="item">
          <div class="header">
            <XCheckbox
              v-model="report.add_scheduling"
              :read-only="cannotEditReport"
              value="AddScheduling"
              @change="onAddScheduling"
            />
            <h5
              id="report_schedule"
              class="schedule-title"
              @click="toggleScheduling"
            >Email Configuration</h5>
          </div>
          <div class="email-description">
            Scheduled email with the report attached will be sent
          </div>
          <div class="inner-content schedule">
            <XArrayEdit
              v-if="report.add_scheduling"
              ref="mail_ref"
              v-model="report.mail_properties"
              :schema="mailSchema"
              :read-only="cannotEditReport"
              @validate="onValidate"
            />
            <div
              v-if="report.add_scheduling"
              id="report_frequency"
            >
              <h4 class="email-title">
                Email Recurrence
              </h4>
              <XRecurrence
                v-model="report"
                :read-only="cannotEditReport"
                @validate="validateSendTime"
              />
            </div>
          </div>
        </div>

      </div>
      <div class="x-section x-btn-container footer">
        <div class="error-text">
          {{ error }}
        </div>
        <div>
          <XButton
            v-if="!hideTestNow"
            id="test-report"
            type="inverse"
            @click="runNow"
          >Send Email</XButton>
          <XButton
            v-if="!hideDownloadNow"
            id="reports_download"
            type="inverse-emphasize"
            :disabled="disableDownloadReport"
            :loading="downloading"
            @click="startDownload"
          >
            Download Report
          </XButton>
          <XButton
            id="report_save"
            type="primary"
            :disabled="!valid"
            @click="saveExit"
          >Save</XButton>
        </div>
      </div>
    </XBox>
  </XPage>
</template>

<script>
import Vue from 'vue';
import PulseLoader from 'vue-spinner/src/PulseLoader.vue';
import {
  mapState, mapMutations, mapActions, mapGetters,
} from 'vuex';
import { Modal } from 'ant-design-vue';
import XPage from '../axons/layout/Page.vue';
import XBox from '../axons/layout/Box.vue';
import XButton from '../axons/inputs/Button.vue';
import XCheckbox from '../axons/inputs/Checkbox.vue';
import XSelectSymbol from '../neurons/inputs/SelectSymbol.vue';
import XSelect from '../axons/inputs/select/Select.vue';
import XRecurrence from '../axons/inputs/Recurrence.vue';
import {
  formatDate, weekDays, monthDays, getTimeZoneDiff,
} from '../../constants/utils';
import { SpaceTypesEnum } from '../../constants/dashboard';
import viewsMixin from '../../mixins/views';
import XArrayEdit from '../neurons/schema/types/array/ArrayEdit.vue';
import configMixin from '../../mixins/config';
import { SHOW_TOASTER_MESSAGE, REMOVE_TOASTER } from '../../store/mutations';


import {
  FETCH_REPORT, SAVE_REPORT, RUN_REPORT, DOWNLOAD_REPORT,
} from '../../store/modules/reports';
import { FETCH_DASHBOARD_SPACES } from '../../store/modules/dashboard';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../store/modules/onboarding';
import { REPORT_GENERATED } from '../../constants/getting-started';
import { DATE_FORMAT } from '../../store/getters';

export default {
  name: 'XReport',
  components: {
    XPage, XBox, XButton, XSelect, XCheckbox, XSelectSymbol, XArrayEdit, PulseLoader, XRecurrence,
  },
  mixins: [viewsMixin, configMixin],
  data() {
    return {
      report: {
        include_dashboard: false,
        send_csv_attachments: true,
        spaces: [],
        include_saved_views: false,
        views: [{ entity: '', id: '' }],
        recipients: [],
        add_scheduling: null,
        period: 'daily',
        period_config: {
          week_day: 0,
          monthly_day: 1,
          send_time: '13:00',
        },
        mail_properties: {
          mailSubject: '',
          mailMessage: '',
          emailList: [],
          emailListCC: [],
        },
      },
      downloading: false,
      queryValidity: false,
      scheduleValidity: false,
      toastTimeout: 2500,
      validity: {
        fields: [], error: '',
      },
      lastGenerated: null,
      lastGeneratedTitle: null,
      canSendEmail: false,
      isLatestReport: false,
      loading: false,
      timeModal: false,
    };
  },
  computed: {
    ...mapState({
      reportData(state) {
        return state.reports.current.data;
      },
      reportFetching(state) {
        return state.reports.current.fetching;
      },
      dashboardSpaces(state) {
        const customSpaces = state.dashboard.spaces.data
          .filter((space) => space.type === SpaceTypesEnum.custom);
        const defaultSpace = state.dashboard.spaces.data
          .find((space) => space.type === SpaceTypesEnum.default);
        if (defaultSpace) {
          customSpaces.unshift(defaultSpace);
        }
        return customSpaces.map((space) => ({ name: space.uuid, title: space.name }));
      },
    }),
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    canViewDashboard() {
      return this.$can(this.$permissionConsts.categories.Dashboard,
        this.$permissionConsts.actions.View);
    },
    cannotEditReport() {
      return this.$cannot(this.$permissionConsts.categories.Reports,
        this.$permissionConsts.actions.Update) && this.id !== 'new';
    },
    disableDownloadReport() {
      return this.downloading;
    },
    id() {
      return this.$route.params.id;
    },
    name() {
      if (!this.reportData || !this.reportData.name) return 'New Report';

      return this.reportData.name;
    },
    hideTestNow() {
      if (!this.report.last_generated) {
        return true;
      }
      return !this.canSendEmail;
    },
    hideDownloadNow() {
      return !this.report.last_generated;
    },
    valid() {
      if (this.cannotEditReport) {
        return false;
      }
      if (!this.report.name) {
        return false;
      }
      if (!this.report.include_dashboard && !this.report.include_saved_views) {
        return false;
      }
      if (this.report.include_saved_views) {
        if (!this.queryValidity) {
          return false;
        }
      }
      if (this.report.add_scheduling) {
        if (this.validity.error) {
          return false;
        }
      }
      return !this.validity.error;
    },
    error() {
      if (!this.report.name) {
        return 'Report Name is a required field';
      }
      if (!this.report.include_dashboard && !this.report.include_saved_views) {
        return 'You must include the dashboard or "Saved Views"';
      }
      if (this.report.include_saved_views) {
        if (!this.queryValidity) {
          return 'Configuration for “include Saved Queries data” is invalid';
        }
      }
      if (this.report.add_scheduling) {
        return this.validity.error;
      }
      return this.validity.error;
    },
    spacesSchema() {
      return {
        name: 'spaces_config',
        title: 'Dashboard spaces:',
        items: {
          title: '',
          name: 'uuid',
          type: 'string',
          enum: this.dashboardSpaces,
        },
        type: 'array',
      };
    },
    mailSchema() {
      return {
        name: 'mail_config',
        title: '',
        items: [
          {
            name: 'mailSubject',
            title: 'Subject',
            type: 'string',
            required: true,
          },
          {
            name: 'mailMessage',
            title: 'Custom message (up to 500 characters)',
            type: 'string',
            format: 'text',
            limit: 500,
            required: false,
          },
          {
            name: 'emailList',
            title: 'Recipients',
            type: 'array',
            items: {
              type: 'string',
              format: 'email',
            },
            required: true,
          },
          {
            name: 'emailListCC',
            title: 'Recipients CC',
            type: 'array',
            items: {
              type: 'string',
              format: 'email',
            },
            required: false,
          },
        ],
        required: [
          'mailSubject', 'emailList',
        ],
        type: 'array',
      };
    },
    recurrence: {
      get() {
        return {
          period: this.report.period,
          period_config: this.report.period_config,
        };
      },
      set(newValue) {
        this.report.period = newValue.period;
        this.report.period_config = newValue.period_config;
        this.$forceUpdate();
      },
    },
  },
  async created() {
    this.loading = true;
    if (this.canViewDashboard) {
      await this.fetchDashboard();
    }
    if (!this.reportFetching && (!this.reportData.uuid || this.reportData.uuid !== this.id)) {
      this.loading = true;
      await this.fetchReport(this.id);
    }
    if (this.reportData.error) {
      Modal.confirm({
        title: 'This report cannot be viewed.',
        content: 'You are missing permissions for at least one dashboard space included in this report.',
        cancelButtonProps: { style: { display: 'none' } },
        icon: 'exclamation-circle',
        centered: true,
        onOk: () => this.exit(),
      });
    } else {
      this.initData();
    }
    this.loading = false;
  },
  mounted() {
    if (this.$refs.name) {
      this.$refs.name.focus();
    }
  },
  methods: {
    ...mapMutations({
      showToasterMessage: SHOW_TOASTER_MESSAGE,
      removeToaster: REMOVE_TOASTER,
    }),
    ...mapActions({
      fetchReport: FETCH_REPORT,
      saveReport: SAVE_REPORT,
      runReport: RUN_REPORT,
      downloadReport: DOWNLOAD_REPORT,
      fetchDashboard: FETCH_DASHBOARD_SPACES,
      milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION,
    }),
    initData() {
      if (this.reportData && this.reportData.name) {
        this.report = this.reportData ? { ...this.reportData } : {};
        if (this.report.views === undefined) {
          this.report.views = [];
        }
        if (this.report.views.length === 0) {
          this.report.views.push({ entity: '', name: '' });
        }
        if (!this.report.spaces) {
          this.report.spaces = [];
        }
        if (!this.report.period_config) {
          this.report.period_config = {
            send_time: '08:00',
            week_day: weekDays[0].name,
            monthly_day: monthDays[0].name,
          };
        }

        if (!this.report.mail_properties.mailMessage) {
          this.report.mail_properties.mailMessage = '';
        }

        if (this.report.spaces.length > 0 && this.canViewDashboard) {
          const validDashboardSpaces = this.dashboardSpaces
            .reduce((map, space) => ({ ...map, [space.name]: space.title }), {});
          this.report.spaces = this.report.spaces.filter((space) => validDashboardSpaces[space]);
          if (this.report.spaces.length === 0) {
            this.report.include_dashboard = false;
          }
        }
        if (this.report.last_generated == null) {
          this.isLatestReport = false;
        } else {
          if (this.report.add_scheduling && this.report.mail_properties.emailList.length > 0) {
            this.canSendEmail = true;
          }
          const formattedDate = formatDate(this.report.last_generated, undefined, this.dateFormat);
          if (formattedDate !== this.report.last_generated) {
            this.lastGenerated = `Last generated: ${formattedDate}`;
            this.lastGeneratedTitle = `${this.lastGenerated} ${getTimeZoneDiff()}`;
            this.isLatestReport = true;
          } else {
            this.isLatestReport = false;
          }
        }
      }
      this.validateSavedQueries();
    },
    startDownload() {
      if (this.disableDownloadReport) return;
      this.downloading = true;
      this.downloadReport({ reportId: this.id, name: this.report.name }).then(() => {
        this.downloading = false;
      }).catch((error) => {
        this.downloading = false;
        this.showToaster(error.response.data.message, this.toastTimeout);
      });
    },
    onAddScheduling() {
      const actionName = this.settingToActions.mail[0];
      this.checkEmptySettings(actionName);
      if (this.anyEmptySettings) {
        this.report.add_scheduling = false;
        return;
      }
      setTimeout(() => {
        if (this.report.add_scheduling) {
          this.$refs.mail_ref.validate();
        } else {
          this.removeEmailValidations();
        }
      });
    },
    toggleScheduling() {
      if (this.cannotEditReport) {
        return;
      }
      this.report.add_scheduling = !this.report.add_scheduling;
      this.onAddScheduling();
      this.$forceUpdate();
    },
    removeEmailValidations() {
      const fieldsToRemove = [];
      this.validity.fields.forEach((field, index) => {
        if (this.mailSchema.items.find((item) => `${this.mailSchema.name}.${item.name}` === field.name)) {
          fieldsToRemove.push(index);
        }
      });
      fieldsToRemove.forEach((fieldIndex, index) => {
        if (this.validity.fields.length > 0) {
          this.validity.fields.splice(fieldIndex - index, 1);
        }
      });
      if (this.validity.fields.length === 0) {
        this.validity.error = '';
      } else {
        this.validity.fields.forEach((field) => {
          this.onValidate(field);
        });
      }
    },
    runNow() {
      const self = this;
      self.runReport(this.report).then(() => {
        this.showToaster('Email is being sent', this.toastTimeout);
        setTimeout(() => {
          this.showToaster('Email sent successfully', this.toastTimeout);
        });
      }).catch((error) => {
        this.validity.error = error.response.data.message;
      });
    },
    saveExit() {
      this.showToaster('Saving the report...', this.toastTimeout);
      this.saveReport(this.report).then(
        () => {
          this.milestoneCompleted({ milestoneName: REPORT_GENERATED });
          this.showToaster('Report is saved and being generated in the background', this.toastTimeout);
          this.exit();
        },
      ).catch((error) => {
        if (error.response.status === 400) this.validity.fields.push('name');
        this.validity.error = error.response.data;
        this.removeToaster();
      });
    },
    exit() {
      this.$router.push({ name: 'Reports' });
    },
    onEntityChange(name, index) {
      Vue.set(this.report.views, index, { entity: name, id: '' });
      this.$forceUpdate();
      this.validateSavedQueries();
    },
    addQuery() {
      this.report.views.push({ entity: '', name: '' });
      this.$forceUpdate();
      this.validateSavedQueries();
    },
    removeQuery(index) {
      this.report.views.splice(index, 1);
      this.$forceUpdate();
      this.validateSavedQueries();
    },
    onQueryNameChange(id, index) {
      Vue.set(this.report.views, index, { entity: this.report.views[index].entity, id });
      this.$forceUpdate();
      this.validateSavedQueries();
    },
    canEditSavedView(index) {
      if (this.cannotEditReport) {
        return false;
      }
      if (this.report.views[index] && this.report.views[index].entity) {
        return Boolean(this.publicViews[this.report.views[index].entity]);
      }
      return true;
    },
    currentViewOptions(index) {
      if (!this.report.views[index]) {
        return [];
      }
      const { entity, id } = this.report.views[index];
      return this.viewSelectOptionsGetter(true)(entity, id);
    },
    onNameChanged() {
      if (this.validity.error && this.validity.fields.length === 1 && this.validity.fields[0] === 'name') {
        this.validity.error = '';
        this.validity.fields.pop();
      }
    },
    validateSavedQueries() {
      let result = true;
      if (!this.report.include_saved_views) {
        this.queryValidity = result;
        return;
      }
      if (this.report.views && this.report.views.length === 0) {
        result = false;
      }
      this.report.views.forEach((view) => {
        if (!view.entity || !view.id) {
          result = false;
        }
      });
      this.queryValidity = result;
    },
    onValidate(field) {
      let validityChanged = false;
      this.validity.fields = this.validity.fields.filter((x) => x.name !== field.name);
      if (!field.valid) {
        this.validity.fields.push(field);
      }
      if (field.error) {
        if (!this.validity.error) {
          validityChanged = true;
        }
        this.validity.error = field.error;
      } else {
        const nextInvalidField = this.validity.fields.find((x) => x.error);
        const nextResult = nextInvalidField ? nextInvalidField.error : '';
        if (nextResult !== this.validity.error) {
          validityChanged = true;
        }
        this.validity.error = nextResult;
      }
      if (validityChanged) {
        this.$forceUpdate();
      }
    },
    showToaster(message, timeout = 2500) {
      this.showToasterMessage({ message, timeout });
    },
    validateSendTime(isSendTimeValid) {
      const getTimePickerError = ((i) => i.field === 'send_time');
      if (!isSendTimeValid) {
        // Add error the the validity fields if the time is invalid
        this.validity.error = 'Send time is invalid';
        const sendTimePickerError = this.validity.fields.find(getTimePickerError);
        if (!sendTimePickerError) {
          this.validity.fields.push({ field: 'send_time', error: this.validity.error });
        }
      } else {
        // If the send time is valid and there is an error than removed it
        const sendTimeError = this.validity.fields.find(getTimePickerError);
        if (sendTimeError) {
          this.validity.fields = this.validity
            .fields.filter((error) => error.field !== sendTimeError.field);
          if (this.validity.fields.length === 0) {
            this.validity.error = '';
          }
        }
      }
    },
  },
};
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
                padding-top: 0;
                padding-bottom: 0;

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

                .schedule-title {
                    margin: 0 0 0 8px;
                    cursor: pointer;
                }
            }

            .item {
                align-items: flex-end;
                width: 100%;
                display: inline-block;

              .email-title {
                margin-top: 22px;
                margin-bottom: 22px;
              }

                .report-name-label {
                    padding-right: 12px;
                }

                .report-name-textbox {
                    width: 200px;
                    line-height: 24px;
                }

                .main {
                    margin-left: 24px;

                    .report-title {
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

        .save-queries-desc {
            padding-left: 24px;
            padding-bottom: 12px;
        }

      .dashboard-spaces {
          margin-left: 24px;

          .x-array-edit {
            display: grid;

            grid-template-columns: 120px auto;

            .md-field {
              min-height: 24px;
              line-height: 24px;
              margin-bottom: 12px;
              padding-top: 0;
              margin-top: 0;
            }
          }
      }

        .saved-queries {
            display: grid;
            grid-template-columns: 1fr;
            grid-gap: 12px 24px;
            align-items: center;
            margin-left: 24px;
            .saved-query {
                flex: 1 0 auto;

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
          .list {
            display: grid;
            grid-template-columns: 1fr;
            grid-gap: 12px 24px;
          }

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

</style>
