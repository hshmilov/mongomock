import xSidePanel from '@networks/side-panel/SidePanel.vue';
import xButton from '@axons/inputs/Button.vue';

import './compliance-panel.scss';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import { mapMutations } from 'vuex';
import _capitalize from 'lodash/capitalize';
import _isNil from 'lodash/isNil';

/**
 * @param {any} value - the input value to validate against
 * @this {VueInstance} the component instance
 * @description custom vuelidate validator - validates query names are unique
 * @returns {Boolean} true if valid
 */

export default {
  name: 'xCompliancePanel',
  components: {
    xSidePanel,
    xButton,
  },
  props: {
    data: {
      type: Object,
    },
    fields: {
      type: Array,
    },
  },
  data() {
    return {
      expandedValues: [],
    };
  },
  mounted() {
    this.updateActivePanels();
  },
  computed: {
    filteredFields() {
      return this.fields.filter((field) => field.expanded !== undefined);
    },
  },
  methods: {
    ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
    updateActivePanels() {
      this.expandedValues = [];
      this.filteredFields.forEach((field, index) => {
        if (field.expanded) {
          this.expandedValues.push(index);
        }
      });
    },
    renderFields() {
      return this.filteredFields.map((field) => {
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
          <div class="rule">
            <h5>
              Rule
            </h5>
            <p>
              {this.data.rule}
            </p>
          </div>
          <div class="category">
            <h5>
              Category
            </h5>
            <p>
              {this.data.category}
            </p>
          </div>
          <v-expansion-panels
            value={this.expandedValues}
            multiple
            accordion
          >
            {this.renderFields()}
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
                  <x-button onClick={this.runQueryOnAffectedEntities}>
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
  },
  render(h) {
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
