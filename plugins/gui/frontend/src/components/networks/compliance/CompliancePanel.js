import xSidePanel from '@networks/side-panel/SidePanel.vue';

import './compliance-panel.scss';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import { mapMutations } from 'vuex';
import { DEFAULT_DATE_SCHEMA } from '@store/modules/constants';
import _capitalize from 'lodash/capitalize';
import _isNil from 'lodash/isNil';
import _get from 'lodash/get';
import { getEntityPermissionCategory } from '@constants/entities';
import XStringView from '@neurons/schema/types/string/StringView.vue';
import ComplianceComments from '@components/networks/compliance/ComplianceComments.vue';

const nonExpandablePanelFields = [{
  name: 'rule', title: 'Rule', type: 'string',
}, {
  name: 'category', title: 'Category', type: 'string',
}, {
  name: 'account', title: 'Account', type: 'array', items: { type: 'string' },
}];

const expandablePanelFields = [{
  name: 'description', title: 'Description', type: 'text', expanded: true,
}, {
  name: 'remediation', title: 'Remediation', type: 'text', expanded: false,
}, {
  name: 'entities_results', title: 'Results', type: 'text', expanded: true,
}, {
  name: 'error', title: 'Error', type: 'text', expanded: true,
}, {
  name: 'comments', title: 'Comments', type: 'array', expanded: true,
}, {
  name: 'cis', title: 'CIS Controls', type: 'text', expanded: true,
}];

export default {
  name: 'xCompliancePanel',
  components: {
    xSidePanel,
    XStringView,
    ComplianceComments,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
    },
    fields: {
      type: Array,
    },
    cisName: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      expandedValues: [],
    };
  },
  computed: {
    canViewEntities() {
      if (!this.data.entities_results_query) {
        return false;
      }
      return this.$can(getEntityPermissionCategory(this.data.entities_results_query.type),
        this.$permissionConsts.actions.View);
    },
    expandablePanelFieldsToDisplay() {
      const shouldDisplayResultField = (item) => !(item.name === 'entities_results' && _get(this.data, 'status') === 'Passed');
      return expandablePanelFields.filter(shouldDisplayResultField);
    },
  },
  mounted() {
    this.updateActivePanels();
  },
  methods: {
    ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
    updateActivePanels() {
      this.expandedValues = [];
      this.expandablePanelFieldsToDisplay.forEach((field, index) => {
        if (field.expanded) {
          this.expandedValues.push(index);
        }
      });
    },
    renderNonExpandableFields() {
      return nonExpandablePanelFields.map((field) => (
        <div class="{field.name}">
          <h5>
            {field.title}
          </h5>
          <p>
            {this.getFieldValue(field.type, this.data[field.name])}
          </p>
        </div>
      ));
    },
    getFieldValue(type, value) {
      if (type === 'array') {
        return value.join(', ');
      }
      return value;
    },
    shouldSkipPanel(field) {
      if (field.name === 'comments') {
        if (this.$cannot(this.$permissionConsts.categories.Compliance,
          this.$permissionConsts.actions.Update,
          this.$permissionConsts.categories.Comments) && !this.data.comments.length) {
          return true;
        }
        return false;
      }
      return !this.data[field.name];
    },
    renderExpandableFields() {
      return this.expandablePanelFieldsToDisplay.map((field) => {
        if (this.shouldSkipPanel(field)) return null;
        return (
          <v-expansion-panel>
            <v-expansion-panel-header>
              <h5>
                {field.title}
              </h5>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              {
                field.name === 'comments'
                  ? <compliance-comments comments={this.data[field.name]} accounts={this.data.account}
                  cisName={this.cisName} section={this.data.section}
                  onUpdateComments={(data) => this.$emit('updateComments', data)} />
                  : this.data[field.name]
              }
            </v-expansion-panel-content>
          </v-expansion-panel>
        );
      });
    },
    onClose() {
      this.$emit('close');
    },
    runQueryOnAffectedEntities() {
      /*
      Open the entities screen with a query that shows
      the devices/users that affected the current rule
       */
      const query = {
        module: this.data.entities_results_query.type,
        filter: this.data.entities_results_query.query,
      };
      if (_isNil(query.filter)) {
        return;
      }
      this.updateView({
        module: query.module,
        view: {
          query: {
            filter: query.filter,
          },
        },
        name: this.data.rule,
        uuid: null,
      });
      this.$router.push({ path: `/${query.module}` });
    },
    renderBody() {
      if (!this.data) {
        return null;
      }
      return (
        <div slot="panelContent" class="body">
          <div class="last-updated">
            <p class="last-updated__title">
              Last updated:
            </p>
            <XStringView
              schema={this.DEFAULT_DATE_SCHEMA}
              value={this.data.last_updated}
            />
          </div>
          {
            this.renderNonExpandableFields()
          }
          <v-expansion-panels
            value={this.expandedValues}
            multiple
            accordion
          >
            {this.renderExpandableFields()}
          </v-expansion-panels>
        </div>
      );
    },
    renderFooter() {
      if (!this.data) {
        return null;
      }
      return (
        <div slot="panelFooter">
          <div class="status-container">
            <div class={`status ${this.data.status.toLowerCase().replace(' ', '-')}`}/>
            <div class="status-text">{this.data.status}</div>
            { this.shouldDisplayResult() ? <div class="results-text" >{this.data.results}</div> : null }
          </div>
          <div class="buttons">
            {
              // conditionally render action button in footer
              this.data.status !== 'No data' && this.data.entities_results_query
                ? [
                  <x-button
                    type="primary"
                    disabled={!this.canViewEntities}
                    onClick={this.runQueryOnAffectedEntities}
                  >
                    Show Affected {
                    _capitalize(this.data.entities_results_query.type)
                  }
                  </x-button>,
                ]
                : ''
            }
          </div>
        </div>
      );
    },
    shouldDisplayResult() {
      const data = this.data.status !== 'No Data';
      try {
        const passedRules = parseInt(this.data.results.split('/')[0], 10);
        return data && passedRules;
      } catch (e) {
        return false;
      }
    },
    getSidePanelContainer() {
      return document.querySelector('.x-cloud-compliance');
    },
  },
  created() {
    this.DEFAULT_DATE_SCHEMA = DEFAULT_DATE_SCHEMA;
  },
  render() {
    return (
      <x-side-panel
        visible={this.visible}
        panel-container={this.getSidePanelContainer}
        panelClass='compliance-panel'
        title={this.data ? `${this.data.section} ${this.data.rule}` : ''}
        onClose={this.onClose}
      >
        {
          this.renderBody()
        }
        {
          this.renderFooter()
        }
      </x-side-panel>
    );
  },
};
