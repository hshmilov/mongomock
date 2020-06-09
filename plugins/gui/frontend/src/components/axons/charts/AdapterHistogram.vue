<template>
  <div class="x-adapter-histogram">
    <XHistogram
      :data="data"
      :condensed="true"
      :limit="5"
      v-on="$listeners"
    >
      <div
        slot="footer"
        class="adapter-histogram-footer"
      >
        {{ totalCountLabel }}
        <strong
          v-if="data.length"
          class="device-count"
        >{{ data[0].uniqueDevices }}</strong>
      </div>
    </XHistogram>
  </div>
</template>

<script>
import XHistogram from './Histogram.vue';

export default {
  name: 'XAdapterHistogram',
  components: { XHistogram },
  props: {
    data: {
      type: Array,
      required: true,
    },
  },
  computed: {
    totalCountLabel() {
      const [adaptersData] = this.data;
      const module = adaptersData ? adaptersData.module : '';
      return `Total unique ${module}`;
    },
  },
};

</script>

<style lang="scss">

.x-adapter-histogram {
  .adapter-histogram-footer {
    width: 100%;
    display: flex;
    justify-content: center;

    .device-count {
      margin-left: 4px;
    }
  }
}

</style>
