<template>
  <div
    v-if="footerMessage"
    class="x-bottom-bar"
  >
    <VFooter
      :color="bgColor"
      :fixed="true"
    >
      <div class="footer-content">
        {{ footerMessage }}
      </div>
    </VFooter>
  </div>
</template>

<script>
import _get from 'lodash/get';
import { mapGetters, mapActions, mapMutations } from 'vuex';
import { GET_FOOTER_MESSAGE } from '../../../store/getters';
import { GET_ENVIRONMENT_NAME } from '../../../store/actions';
import { UPDATE_FOOTER_MESSAGE } from '../../../store/mutations';

export default {
  name: 'XBottomBar',
  props: {
    bgColor: {
      type: String,
      default: '#D4D2D2',
    },
  },
  computed: {
    ...mapGetters({
      footerMessage: GET_FOOTER_MESSAGE,
    }),
  },
  async mounted() {
    const environmentNameResponse = await this.getEnvironmentName();
    const footerMessage = _get(environmentNameResponse, 'data.environment_name', '');
    this.updateFooterMessage(footerMessage);
  },
  methods: {
    ...mapActions({
      getEnvironmentName: GET_ENVIRONMENT_NAME,
    }),
    ...mapMutations({
      updateFooterMessage: UPDATE_FOOTER_MESSAGE,
    }),
  },
};

</script>

<style lang="scss">
  .footer-content {
    color: $theme-black;
    width: 100%;
    text-align: center;
  }
</style>
