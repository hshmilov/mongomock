import Vue from 'vue';
import { mapState } from 'vuex';
import xPage from '../axons/layout/Page.vue';
import xQueriesTable from '../networks/saved-queries/QueriesTable.vue';

const SavedQueriesPageCreator = (props) => {
  const { permissionLevel, module } = props;
  return Vue.component('SavedQueries', {
    components: { xPage, xQueriesTable },
    computed: mapState({
      isReadOnly(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions[permissionLevel] === 'ReadOnly';
      },
    }),
    // eslint-disable-next-line no-unused-vars
    render(h) {
      return (
        <x-page breadcrumbs={[
          { title: module, path: { name: permissionLevel } },
          { title: 'Saved Queries' },
        ]}>
            <x-queries-table namespace={module} read-only={this.isReadOnly}/>
        </x-page>
      );
    },
  });
};

export default SavedQueriesPageCreator;
