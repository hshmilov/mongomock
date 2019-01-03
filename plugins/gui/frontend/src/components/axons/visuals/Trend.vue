<template>
    <svg viewBox="0 0 136 84" class="x-trend" :class="value">
        <path v-if="value === 'negative'" class="svg-fill"
              d="M131,0 L104.288053,2.54399491 L117.008028,22.8959542 L131,0 Z M4.05999788,81.6959966 L113.47826,13.3095827 L115.174257,12.2495848 L113.054261,8.85759159 L111.358264,9.91758947 L1.94000212,78.3040034 L0.244005512,79.3640013 L2.36400127,82.7559945 L4.05999788,81.6959966 Z"
              fill-rule="nonzero"></path>
        <path v-if="value === 'positive'" class="svg-fill"
              d="M131,83 L117.008028,60.1040458 L104.288053,80.4560051 L131,83 Z M1.94000212,4.69599661 L111.358264,73.0824105 L113.054261,74.1424084 L115.174257,70.7504152 L113.47826,69.6904173 L4.05999788,1.30400339 L2.36400127,0.244005512 L0.244005512,3.63599873 L1.94000212,4.69599661 Z"
              fill-rule="nonzero"></path>
    </svg>
</template>

<script>
    export default {
        name: 'x-trend',
        props: {value: {default: 'positive'}}
    }
</script>

<style lang="scss">
    .x-trend {
        &.positive {
            .svg-fill {
                fill: $indicator-success;
            }
        }

        &.negative {
            .svg-fill {
                fill: $indicator-error;
            }
        }
    }
</style>