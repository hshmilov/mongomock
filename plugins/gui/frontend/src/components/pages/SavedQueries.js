import Vue from 'vue'
import xPage from '../axons/layout/Page.vue'
import xQueriesTable from '../networks/saved-queries/QueriesTable.vue'

import { mapState } from 'vuex'
const SavedQueriesPageCreator = (props) => {
    const { permissionLevel, module } = props;
    return Vue.component('SavedQueries', {
        components: {xPage, xQueriesTable},
        computed: mapState({
            isReadOnly(state) {
                const user = state.auth.currentUser.data
                if (!user || !user.permissions) return true
                return user.permissions[permissionLevel] === 'ReadOnly'
            }
        }),
        render(h) {
            return (
                <x-page breadcrumbs={[
                    { title: module , path: { name: permissionLevel }},
                    { title: 'Saved Queries' }
                ]}>
                    <x-queries-table module={module} read-only={this.isReadOnly}/>
                </x-page>
            )
        }
    })
}

export const xDevicesSavedQueries = SavedQueriesPageCreator({module: 'devices', permissionLevel: 'Devices'})
export const xUsersSavedQueries = SavedQueriesPageCreator({module: 'users', permissionLevel: 'Users'})