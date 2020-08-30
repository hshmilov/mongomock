import { required, maxLength } from 'vuelidate/lib/validators';

import { mapActions, mapGetters } from 'vuex';
import _get from 'lodash/get';
import _isNull from 'lodash/isNull';
import _stubTrue from 'lodash/stubTrue';
import _cond from 'lodash/cond';
import _isEmpty from 'lodash/isEmpty';

import xFilter from '@neurons/schema/query/Filter.vue';
import xStringView from '@neurons/schema/types/string/StringView.vue';
import xButton from '@axons/inputs/Button.vue';
import xSelectBox from '@axons/inputs/select/SelectBox.vue';
import xSidePanel from '@networks/side-panel/SidePanel.vue';
import { xActionItem, xActionsGroup } from '@networks/side-panel/PanelActions';
import xCombobox from '@axons/inputs/combobox/index.vue';
import { LAZY_FETCH_DATA_FIELDS } from '@store/actions';

import { mdiPencil, mdiDelete, mdiEyeOutline } from '@mdi/js';

import './saved-query-panel.scss';

import { fetchEntityTags, fetchEntitySavedQueriesNames } from '@api/saved-queries';
import { getEntityPermissionCategory, EntitiesEnum as Entities } from '@constants/entities';
import { isEmptyExpression } from '@/logic/expression';

/**
 * @param {any} value - the input value to validate against
 * @this {VueInstance} the component instance
 * @description custom vuelidate validator - validates query names are unique
 * @returns {Boolean} true if valid
 */
const uniqueQueryName = function uniqueQueryName(value) {
  if ((this.editingMode && value === this.query.name) || _isEmpty(value)) return true;
  return !this.existingQueriesNamesList.has(value.toLocaleLowerCase());
};

export default {
  name: 'xSavedQueriesPanel',
  components: {
    xFilter,
    xStringView,
    xButton,
    xSidePanel,
    xActionItem,
    xActionsGroup,
    xSelectBox,
    xCombobox,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    namespace: {
      required: true,
      type: String,
    },
  },
  validations: {
    name: {
      required,
      uniqueQueryName,
    },
    description: {
      maxLength: maxLength(300),
    },
  },
  data() {
    return {
      editingMode: false,
      queryFieldsProxies: {
        name: null,
        description: null,
        tags: null,
      },
      schemas: {
        lastUpdate: {
          name: 'last_updated', title: 'Last Updated', type: 'string', format: 'date-time',
        },
        updatedBy: {
          name: 'updated_by', title: 'Updated By', type: 'string', format: 'user',
        },
      },
      entityTags: [],
      existingQueriesNamesList: new Set(),
      keepPanelStatic: false,
    };
  },
  computed: {
    ...mapGetters({ getSavedQueryById: 'getSavedQueryById', configuredAdaptersFields: 'configuredAdaptersFields' }),
    queryId() {
      return this.$route.params.queryId;
    },
    query() {
      return this.getSavedQueryById(this.queryId, this.namespace) || {};
    },
    expressions() {
      return _get(this.query, 'view.query.expressions', []);
    },
    permissionCategory() {
      return getEntityPermissionCategory(this.namespace);
    },
    userCannotAddSavedQueries() {
      return this.$cannot(this.permissionCategory,
          this.$permissionConsts.actions.Add, this.$permissionConsts.categories.SavedQueries);
    },
    userCannotRunSavedQueries() {
      return this.$cannot(this.permissionCategory,
        this.$permissionConsts.actions.Run, this.$permissionConsts.categories.SavedQueries)
        && !this.query.private;
    },
    userCannotEditSavedQueries() {
      return this.$cannot(this.permissionCategory,
        this.$permissionConsts.actions.Update, this.$permissionConsts.categories.SavedQueries)
        && !this.query.private;
    },
    userCanDeleteSavedQueries() {
      return this.$can(this.permissionCategory,
        this.$permissionConsts.actions.Delete, this.$permissionConsts.categories.SavedQueries)
        || this.query.private;
    },
    userCanNavigateToEnforcement() {
      return this.$can(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.Add)
      && this.$can(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.Update)
      && this.$can(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.View);
    },
    name: {
      get() {
        if (this.editingMode) {
          return _isNull(this.queryFieldsProxies.name)
            ? this.query.name
            : this.queryFieldsProxies.name;
        }
        return this.query.name;
      },
      set(value) {
        this.queryFieldsProxies.name = value;
      },
    },
    description: {
      get() {
        if (this.editingMode) {
          return _isNull(this.queryFieldsProxies.description)
            ? this.query.description
            : this.queryFieldsProxies.description;
        }
        return this.query.description;
      },
      set(value) {
        this.queryFieldsProxies.description = value;
      },
    },
    tags: {
      get() {
        let res = [];
        if (this.editingMode) {
          res = _isNull(this.queryFieldsProxies.tags)
            ? this.query.tags
            : this.queryFieldsProxies.tags;
        } else {
          res = this.query.tags;
        }
        return res;
      },
      set(value) {
        this.queryFieldsProxies.tags = value;
      },
    },
    isPredefined() {
      const { predefined } = this.query;
      return predefined;
    },
    isEditable() {
      return !this.isPredefined;
    },
    adaptersEntityFields() {
      /* adding connection label attribute so we can handle save query with connection label   */
      return this.configuredAdaptersFields(this.namespace,
        ['saved_query', 'specific_data.connection_label']);
    },
  },
  methods: {
    ...mapActions({
      fetchDataFields: LAZY_FETCH_DATA_FIELDS,
    }),
    saveChanges() {
      // validate on submission
      this.$v.$touch();
      if (this.$v.$invalid) return;

      const updated = {
        ...this.query,
        ...(_isNull(this.queryFieldsProxies.name) ? false : { name: this.queryFieldsProxies.name }),
        ...(_isNull(this.queryFieldsProxies.description)
          ? false
          : { description: this.queryFieldsProxies.description }),
        ...(_isNull(this.queryFieldsProxies.tags) ? false : { tags: this.queryFieldsProxies.tags }),
      };

      this.$emit('save-changes', {
        queryData: updated,
        done: this.toggleEditMode,
      });
    },
    async fetchQueriesNames() {
      try {
        let names = await fetchEntitySavedQueriesNames(Entities[this.namespace]);
        names = names.filter((q) => q.name);
        names = names.map((q) => q.name.toLocaleLowerCase());
        this.existingQueriesNamesList = new Set(names);
      } catch (ex) {
        console.error(ex);
      }
    },
    discardChanges() {
      this.reset();
    },
    isValidQueryWithoutExpression() {
      /**
         * The query is valid, but does not include any expressions.
         * Saved with a modified columns selection
         */
      return Array.isArray(this.expressions) && !this.expressions.length;
    },
    isQueryContainsUnsupportedFields() {
      /**
         * The query is valid, but not supported in the current system.
         * The query contains fields of some non-connected adapter
         */
      const isFieldNotSupported = (expression) => {
        const { field } = expression;
        return field && !this.adaptersEntityFields.has(field);
      };
      return this.expressions.some(isFieldNotSupported);
    },
    isQueryContainsOnlyEmptyExpression() {
      /**
        * The query is valid, but only contains the default empty expression.
        */
      return this.expressions.length === 1 && isEmptyExpression(this.expressions[0]);
    },
    setNameField(e) {
      this.name = e.target.value;
      this.$v.name.$touch();
    },
    setDescriptionField(e) {
      this.description = e.target.value;
      this.$v.description.$touch();
    },
    setTagsField(value) {
      this.tags = value;
    },
    reset() {
      this.$v.$reset();
      if (this.editingMode) {
        this.toggleEditMode();
      }
      this.queryFieldsProxies = {
        name: null,
        description: null,
        tags: null,
      };
    },
    newEnforcement() {
      this.$emit('new-enforcement', this.query.uuid);
    },
    setPublic() {
      const queryData = {
        ...this.query,
        private: false,
      };
      this.keepPanelStatic = true;
      this.$emit('set-public', {
        queryData,
        done: () => { this.keepPanelStatic = false },
      });
    },
    closePanel() {
      this.$emit('close');
    },
    async toggleEditMode() {
      this.editingMode = !this.editingMode;
      if (this.editingMode) {
        await this.fetchQueriesNames();
        await this.fetchEntityTags();
      }
    },
    removeQuery() {
      this.$emit('delete', undefined, this.queryId, this.query.private);
    },
    runQuery() {
      this.$emit('run', this.queryId);
    },
    onClose() {
      this.reset();
      this.$emit('close');
    },
    genQueryExpressionMarkup(usecase) {
      return () => {
        switch (usecase) {
          case 'empty':
            return <span>No query defined</span>;
          case 'not_supported':
            return <span>Query not supported for the existing data</span>;
          default:
            return (
                        <x-filter
                            disabled
                            value={[...this.expressions]}
                            module={this.namespace}
                        />
            );
        }
      };
    },
    onTagsSelections(selections) {
      this.tags = selections;
    },
    genTagsMarkup() {
      if (this.editingMode && !_isEmpty(this.entityTags)) {
        return (<x-combobox
                    value={this.tags}
                    onInput={this.onTagsSelections}
                    items={this.entityTags}
                    multiple
                    menuProps={{ maxWidth: 744 }}
                    keep-open={false}
                />);
      }
      return !_isEmpty(this.tags) ? this.tags.map((t) => <v-chip color="rgba(255, 125, 70, 0.2)" small class="chips">{t}</v-chip>) : (<p>No tags associated</p>);
    },
    genDescriptionMarkup() {
      const description = _get(this.query, 'description') || 'No description provided';
      const descriptionError = this.$v.description.$error;

      // return description field markup if in editing mode. Else, return plain text.
      const descriptionMarkup = this.editingMode ? (
        <div class="description">
            {descriptionError && <p class="error-input indicator-error--text">Description is limited to 300 chars</p>}
            <textarea class="description_input" rows="5" value={this.description} onInput={this.setDescriptionField} />
        </div>
      ) : <p>{description}</p>;

      return descriptionMarkup;
    },
    genNameMarkup() {
      // are there any form errors?
      const nameError = this.$v.name.$error;
      const nameRequired = !this.$v.name.required;

      // return name field markup if in editing mode. Else, return null.
      const nameMarkup = this.editingMode ? (
            <div class="name">
                <h5>Name</h5>
                {nameError && <p class="error-input indicator-error--text">{nameRequired ? 'Query Name is a required field' : 'Query Name is used by another query'}</p>}
                <input type="text" class="name_input" value={this.name} onInput={this.setNameField}/>
            </div>
      ) : null;

      return nameMarkup;
    },
    genActionsButtonsMarkup() {
      let actions = [];

      if (!this.editingMode) {
        if (this.query.private && !this.userCannotAddSavedQueries) {
          actions.push(<x-action-item
            class="action-set-public"
            title="Set Public"
            onClick={this.setPublic}
            size="20"
            color="#fff"
            icon={mdiEyeOutline}
          />);
        } else if (this.userCanNavigateToEnforcement && !this.query.private) {
          actions.push(<x-action-item
            class="action-enforce"
            title="New Enforcement"
            onClick={this.newEnforcement}
            size="20"
            color="#fff"
            icon="$vuetify.icons.enforcements"
        />);
        }
        if (this.userCanDeleteSavedQueries) {
          actions.push(<x-action-item
            class="action-remove"
            title="Delete"
            onClick={this.removeQuery}
            size="20"
            color="#fff"
            icon={mdiDelete}
          />);
        }
      }

      if (this.isEditable && !this.editingMode && !this.userCannotEditSavedQueries) {
        actions = [(
          (<x-action-item
                    class="action-edit"
                    title="Edit"
                    onClick={this.toggleEditMode}
                    size="20"
                    color="#fff"
                    icon={mdiPencil}
                />)
        ), ...actions];
      }
      return actions;
    },
    async fetchEntityTags() {
      const tags = await fetchEntityTags(Entities[this.namespace]);
      this.entityTags = tags;
    },
    getSidePanelContainer() {
      return document.querySelector('.x-queries-table');
    },
  },
  created() {
    this.fetchDataFields({ module: this.namespace });
  },
  render() {
    // renderExpression is a function that will return the expression markup
    // based on a givven conditions (valid, empty, not supporteds)
    const renderExpression = _cond([
      [this.isValidQueryWithoutExpression, this.genQueryExpressionMarkup('empty')],
      [this.isQueryContainsOnlyEmptyExpression, this.genQueryExpressionMarkup('empty')],
      [this.isQueryContainsUnsupportedFields, this.genQueryExpressionMarkup('not_supported')],
      [_stubTrue, this.genQueryExpressionMarkup()],
    ]);

    return (
       <x-side-panel
            visible={this.visible}
            mask={!this.keepPanelStatic}
            panel-container={this.getSidePanelContainer}
            panelClass="saved-query-panel"
            title={this.name}
            onClose={this.onClose}



        >
            {
                <x-actions-group slot="panelHeader">
                    {this.genActionsButtonsMarkup()}
                </x-actions-group>

            }
            <div slot="panelContent" class="body">
                {this.genNameMarkup()}
                <div class="description">
                    <h5>Description</h5>
                    {this.genDescriptionMarkup()}
                </div>
                <div class="tags">
                    <h5>Tags</h5>
                    {this.genTagsMarkup()}
                </div>
                <div class="expression">
                    <h5>Query Wizard Expressions</h5>
                    {renderExpression()}
                </div>
                {
                  this.query.predefined
                    ? null
                    : <div class="update">
                        <h5>Last Updated</h5>
                        <xStringView
                            schema={this.schemas.lastUpdate}
                            value={this.query.last_updated}
                        />
                      </div>
                }
                <div class="updater">
                    <h5>Updated By</h5>
                    <xStringView
                        schema={this.schemas.updatedBy}
                        value={this.query.updated_by}
                    />
                </div>
            </div>
            <div slot="panelFooter">
                <div class="buttons">
                    {
                        // conditionally render action button in footer
                        this.editingMode
                          ? [
                                <x-button type="link" onClick={this.discardChanges}>Cancel</x-button>,
                                <x-button
                                  type="primary"
                                  onClick={this.saveChanges}
                                  disabled={this.$v.$error
                                  || this.userCannotEditSavedQueries}>Save</x-button>,
                          ]
                          : <x-button onClick={this.runQuery}
                                      type="primary"
                                      disabled={this.isQueryContainsUnsupportedFields()
                          || this.userCannotRunSavedQueries}>Run Query</x-button>
                    }
                </div>
            </div>
        </x-side-panel>
    );
  },
};
