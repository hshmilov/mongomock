<template>
  <div
    v-if="requirementsList.length"
    class="x-password-policy-requirements"
  >
    <ul class="list">
      <li
        v-for="(requirement, index) in requirementsList"
        :key="index"
        class="list__item"
      >{{ requirement }}</li>
    </ul>
  </div>
</template>

<script>
import { fetchPasswordPolicyRequirements } from '@api/accounts-password.js';
import { passwordPolicyFormatterEnum } from '../../../constants/settings';

export default {
  name: 'XPasswordPolicyRequirements',
  data() {
    return {
      requirementsList: [],
    };
  },
  async mounted() {
    this.requirementsList = this.generateRequirementsList(await fetchPasswordPolicyRequirements());
  },
  methods: {
    generateRequirementsList(requirementsMap) {
      // Last word in the phrase needs 's' in the end to become plural
      const suffixIfPlural = (value, requirement) => (value === 1 ? requirement : `${requirement}s`);
      const formatRequirement = (value, formatter) => suffixIfPlural(value, formatter(value));

      return Object.entries(passwordPolicyFormatterEnum)
        .filter(([name, _]) => requirementsMap[name] !== undefined)
        .map(([name, formatter]) => formatRequirement(requirementsMap[name], formatter));
    },
  },
};
</script>

<style lang="scss">
  .x-password-policy-requirements {
    font-size: 12px;
    padding: 8px;
    border: 1px solid rgba($theme-orange, 0.4);
    border-radius: 8px;

    .list {
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-gap: 2px 8px;

      &__item:before {
        content: '\2022'; /* bullet */
        color: $theme-orange;
        display: inline-block;
        margin-left: 2px;
        width: 8px;
      }
    }
  }
</style>
