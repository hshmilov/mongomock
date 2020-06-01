import _isEmpty from 'lodash/isEmpty';
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
        return this.entityList.reduce((map, module) => ({
          ...map,
          [module]: state[module].views.saved.content.data
            .filter((view) => view)
            .map((view) => ({
              name: view.uuid,
              title: view.name,
              private: view.private,
            })),
        }), {});
      },
      entityOptions() {
        return entities.filter((entity) => this.$canViewEntity(entity.name));
      },
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
    }),
    publicViews() {
      let publicViews = {};
      this.entityList.forEach((entity) => {
        publicViews[entity] = this.views[entity].filter((view) => !view.private);
      });
      return publicViews;
    },
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
      if (this.entityList.includes(this.module)) {
        this.fetchViews({
          module: `${this.module}/views/history`,
          getCount: false,
          limit: 5,
        });
      }
    },
    viewsCallback() {},
    viewSelectOptionsGetter(onlyPublic) {
      let views = onlyPublic ? this.publicViews : this.views;

      return (entity, id) => {
        if (!entity) {
          return [];
        }
        if (!_isEmpty(views[entity])) {
          return views[entity];
        }
        return id ? [{
          name: id,
          title: views[entity] ? 'Loading...' : 'Missing Permissions',
        }] : [];
      }
    }
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
      promises.push(this.fetchViews({ module, getCount: false }));
    });
    Promise.all(promises).then(this.viewsCallback);
  },
};
