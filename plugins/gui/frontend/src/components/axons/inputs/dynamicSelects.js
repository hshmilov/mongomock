import Vue from 'vue';
import { mapActions, mapGetters, mapState } from 'vuex';
import _uniqBy from 'lodash/uniqBy';
import _merge from 'lodash/merge';
import _get from 'lodash/get';
import _property from 'lodash/property';
import { FETCH_DATA_LABELS } from '@store/actions';
import { IS_ENTITY_RESTRICTED } from '@store/modules/auth';
import { FETCH_ADAPTERS, FETCH_ADAPTERS_CLIENT_LABELS } from '@store/modules/adapters';
import XSelect from './select/Select.vue';

// eslint-disable-next-line max-len
const allModulesHaveStateData = (modules, state, mergedParams) => modules.every((usedModule) => _get(state,
  `${usedModule.name}.${mergedParams.moduleAttributeName}${usedModule.dataPath}`,
  false));


const defaultSourceSchema = {
  // default options
  options: {
    // allow add new in the dropdown when no match
    'allow-custom-option': false,
  },
};

const defaultParams = {
  // fetch data action
  action: () => {},
  // list of modules in the root of the state object
  // module object in the form of { name: '', dataPath: '' }
  // where dataPath represent the string path to the options in the state object
  // E.g: state.{{name}}.{{moduleAttributeName}}{{dataPath}}
  modules: [],
  // sub-module of the modules
  moduleAttributeName: '',
  // in case the data in the state object wont have name and title keys
  // a function to normalize the data can be passed here
  optionsNormalizer: (item) => item,
  // keep the default label to missing items ( usually is 'deleted' )
  missingItemsLabel: '',
  // the name of the object parameter representing the name of the option
  // for now its used to unify the option array
  propertyName: 'name',
};

const withDynamicData = (params) => {
  const inheritedProps = { ...XSelect.props };
  const mergedParams = _merge({}, defaultParams, params);
  return Vue.component('withDynamicData', {
    props: {
      ...inheritedProps,
      schema: {
        type: Object,
        default: () => ({}),
      },
      renderLabel: {
        type: Boolean,
        default: false,
      },
      renderLabelText: {
        type: String,
        default: '',
      },
      hideInOneOption: {
        type: Boolean,
        default: false,
      },
    },
    computed: {
      ...mapState({
        [`${mergedParams.moduleAttributeName}`](state) {
          // if one of the sources are not in state, fetch all by return false
          if (allModulesHaveStateData(this.currentModules, state, mergedParams)) {
            const newItems = this.currentModules.reduce((acc, item) => {
              const newModuleItems = _get(state,
                `${item.name}.${mergedParams.moduleAttributeName}${item.dataPath}`,
                []);
              acc.push(...newModuleItems);
              return acc;
            }, []);
            return _uniqBy(newItems, _property(mergedParams.propertyName)).sort();
          }
          // this variable uses 2 states
          // 1: false for no data and this signal fetch data
          // 2: array for having data but it can be empty
          // using it instead of two variable, for data and for fetching
          return false;
        },
      }),
      ...mapGetters({
        isEntityRestricted: IS_ENTITY_RESTRICTED,
      }),
      currentModules() {
        return mergedParams.modules
          .filter((moduleName) => !this.isEntityRestricted(moduleName.name));
      },
    },
    created() {
      if (!this[mergedParams.moduleAttributeName]) {
        this.currentModules.map((usedModule) => {
          this.fetchData({ module: usedModule.name });
          return true;
        });
      }
    },
    methods: {
      ...mapActions({
        fetchData: mergedParams.action,
      }),
      renderSelect(passedProps) {
        const { schema } = passedProps;
        const options = this[mergedParams.moduleAttributeName] || [];
        const normalizedOptions = options.map((option) => mergedParams.optionsNormalizer(option));
        const sourceSchema = _merge(defaultSourceSchema, schema.source || {});
        return (
          <XSelect
            {...passedProps}
            id={this.id}
            value={this.value}
            searchable={this.searchable}
            options={normalizedOptions}
            missingItemsLabel={mergedParams.missingItemsLabel}
            placeholder={passedProps.placeholder || schema.title}
            searchPlaceholder={schema.title}
            allowCustomOption={sourceSchema.options['allow-custom-option']}
            { ...{ on: { ...this.$listeners } } }
          />
        );
      },
      renderWrapperAndLabel(passedProps) {
        const options = this[mergedParams.moduleAttributeName] || [];
        if (this.hideInOneOption && options.length === 1) {
          return false;
        }
        return (
          <div>
            <label for={passedProps.id}>{this.renderLabelText}</label>
            {this.renderSelect(passedProps)}
          </div>
        );
      },
    },
    render(h) {
      const passedProps = this.$props;
      if (this.renderLabel) {
        return this.renderWrapperAndLabel(passedProps);
      }
      return this.renderSelect(passedProps);
    },
  });
};

export const xTagSelect = withDynamicData({
  id: 'tagSelect',
  action: FETCH_DATA_LABELS,
  modules: [
    { name: 'devices', dataPath: '.data' },
    { name: 'users', dataPath: '.data' },
  ],
  moduleAttributeName: 'labels',
});

export const xInstancesSelect = withDynamicData({
  id: 'instanceSelect',
  action: FETCH_ADAPTERS,
  modules: [{ name: 'adapters', dataPath: '' }],
  moduleAttributeName: 'instances',
  optionsNormalizer: (item) => ({ name: item.node_id, title: item.node_name }),
  propertyName: 'node_name',
});

export const xClientConnectionSelect = withDynamicData({
  id: 'connectionLabelSelect',
  action: FETCH_ADAPTERS_CLIENT_LABELS,
  modules: [{ name: 'adapters', dataPath: '' }],
  moduleAttributeName: 'connectionLabels',
  optionsNormalizer: (item) => ({ name: item.label, title: item.label }),
  propertyName: 'label',

});
