<template>
  <XPage
    :breadcrumbs="[
      { title: 'devices', path: { name: 'Devices'}},
      { title: deviceName }
    ]"
  >
    <XEntityView
      module="devices"
      :read-only="isReadOnly"
    />
  </XPage>
</template>

<script>
import { mapState } from 'vuex';
import XPage from '../axons/layout/Page.vue';
import XEntityView from '../networks/entities/view/Layout.vue';


export default {
  name: 'XDevice',
  components: { XPage, XEntityView },
  computed: {
    ...mapState({
      deviceName(state) {
        const current = state.devices.current.data.basic;
        if (!current) return '';

        let name = current['specific_data.data.hostname'];
        if (!name || !name.length) {
          name = current['specific_data.data.name'];
        }
        if (!name || !name.length) {
          name = current['specific_data.data.pretty_id'];
        }
        if (Array.isArray(name) && name.length) {
          return name[0];
        } if (!Array.isArray(name)) {
          return name;
        }
      },
      isReadOnly(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Devices === 'ReadOnly';
      },
    }),
  },
};
</script>

<style lang="scss">

</style>
