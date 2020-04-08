import {
  mapState, mapGetters, mapMutations, mapActions,
} from 'vuex';
import { IS_EXPIRED } from '../store/getters';
import { UPDATE_DATA_VIEW } from '../store/mutations';
import { FETCH_DATA_CONTENT } from '../store/actions';
import { entities } from '../constants/entities';

export default {
  computed: {
    ...mapState({
      views(state) {
        return this.entityList.reduce((map, module) => {
          // eslint-disable-next-line no-param-reassign
          map[module] = state[module].views.saved.content.data
            .filter((view) => view)
            .map((view) => ({ name: view.name, title: view.name, predefined: view.predefined }));
          return map;
        }, {});
      },
      entityOptions() {
        return entities.filter((entity) => this.$canViewEntity(entity.name));
      },
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
    }),
    entityList() {
      return this.entityOptions.map((entity) => entity.name);
    },
  },
  methods: {
    ...mapMutations({
      updateDataView: UPDATE_DATA_VIEW,
    }),
    ...mapActions({
      fetchViews: FETCH_DATA_CONTENT,
    }),
    fetchViewsHistory() {
      this.entityList.forEach((entity) => {
        this.fetchViews({ module: `${entity}/views/history` });
      });
    },
    viewsCallback() {},
  },
  created() {
    if (this.isExpired) return;
    const promises = [];
    this.entityList.forEach((entity) => {
      const module = `${entity}/views/saved`;
      this.updateDataView({
        module,
        view: {
          query: { filter: '', expressions: [] },
        },
      });
      promises.push(this.fetchViews({ module }));
    });
    if (this.entityList.includes('devices')) {
      const module = 'devices/views/template';
      this.updateDataView({
        module,
        view: {
          query: { filter: '', expressions: [] },
        },
      });
      promises.push(this.fetchViews({ module }));
    }
    Promise.all(promises).then(this.viewsCallback);
  },
};
