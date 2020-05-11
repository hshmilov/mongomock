import xSidePanel from '@networks/side-panel/SidePanel.vue';
import XButton from '@axons/inputs/Button.vue';

import './compliance-panel.scss';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import { mapMutations } from 'vuex';
import _capitalize from 'lodash/capitalize';
import _isNil from 'lodash/isNil';
import { formatDate } from '@constants/utils';
import { getEntityPermissionCategory } from '@constants/entities';

const nonExpandablePanelFields = [{
  name: 'rule', title: 'Rule', type: 'string',
}, {
  name: 'category', title: 'Category', type: 'string',
}, {
  name: 'account', title: 'Account', type: 'string',
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
  name: 'cis', title: 'CIS Controls', type: 'text', expanded: true,
}];

export default {
  name: 'xCompliancePanel',
  components: {
    xSidePanel,
    XButton,
  },
  props: {
    data: {
      type: Object,
    },
    fields: {
      type: Array,
    },
    dateFormat: {
      type: String,
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
  },
  mounted() {
    this.updateActivePanels();
  },
  methods: {
    ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
    updateActivePanels() {
      this.expandedValues = [];
      expandablePanelFields.forEach((field, index) => {
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
            {this.data[field.name]}
          </p>
        </div>
      ));
    },
    renderExpandableFields() {
      return expandablePanelFields.map((field) => {
        if (!this.data[field.name]) {
          return null;
        }
        return (
          <v-expansion-panel>
            <v-expansion-panel-header>
              <h5>
                {field.title}
              </h5>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              {this.data[field.name]}
            </v-expansion-panel-content>
          </v-expansion-panel>
        );
      });
    },
    onPanelStateChanged(value) {
      if (!value) {
        this.$emit('close');
      }
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
        selectedView: null,
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
            <p>
              Last updated: {formatDate(this.data.last_updated, undefined, this.dateFormat)}
            </p>
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
            {
              this.data.status !== 'No Data' ? <div class="results-text">{this.data.results}</div> : ''
            }
          </div>
          <div class="buttons">
            {
              // conditionally render action button in footer
              this.data.status !== 'No data' && this.data.entities_results_query
                ? [
                  <XButton
                    type="primary"
                    disabled={!this.canViewEntities}
                    onClick={this.runQueryOnAffectedEntities}
                  >
                    Show Affected {
                    _capitalize(this.data.entities_results_query.type)
                  }
                  </XButton>,
                ]
                : ''
            }
          </div>
        </div>
      );
    },
  },
  render() {
    return (
      <x-side-panel
        value={this.data !== null}
        panelClass="compliance-panel"
        title={this.data ? `${this.data.section} ${this.data.rule}` : ''}
        onInput={this.onPanelStateChanged}
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
