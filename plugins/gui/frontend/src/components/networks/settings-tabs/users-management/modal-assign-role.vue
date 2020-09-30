<template>
  <VDialog
    :value="value"
    width="720"
    persistent
    @click:outside="onCloseModal"
  >
    <VCard
      v-if="value"
      class="x-modal-assign-role"
    >
      <h5 class="modal-assign-role__title">
        {{ `Choose a role for ${count} ${count > 1 ? 'users' : 'user'} selected` }}
      </h5>
      <VSelect
        v-model="selectedRoleId"
        :items="rolesOptions"
        height="40"
        width="240"
        dense
        placeholder="Select Role"
        outlined
      />
      <section class="modal-assign-role__actions">
        <XButton
          type="link"
          @click="onCloseModal"
        >Cancel</XButton>
        <XButton
          type="primary"
          :disabled="roleNotselected"
          @click="callAssignRole"
        >Assign</XButton>
      </section>
    </VCard>
  </VDialog>
</template>

<script>
import { fetchAssignableRolesList } from '@api/roles';

export default {
  name: 'XModalAssignRole',
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    count: {
      type: Number,
      default: 0,
    },
  },
  data() {
    return {
      selectedRoleId: null,
      rolesOptions: [],
    };
  },
  computed: {
    roleNotselected() {
      return !this.selectedRoleId;
    },
  },
  async created() {
    this.rolesOptions = await fetchAssignableRolesList();
  },
  methods: {
    onCloseModal() {
      this.$emit('close');
    },
    callAssignRole() {
      this.$emit('assignrole', this.selectedRoleId);
    },
  },
};
</script>

<style lang="scss">
  .x-modal-assign-role {
    padding: 14px 28px;
    .modal-assign-role__title {
      font-size: 16px;
      color: $theme-black;
      margin-bottom: 28px;
    }

    .v-select.v-text-field input {
    border-style: none;
    visibility: hidden;
    }

    .modal-assign-role__actions {
      display: flex;
      justify-content: flex-end;
    }
  }
</style>
