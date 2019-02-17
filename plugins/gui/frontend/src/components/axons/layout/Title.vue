<template>
    <div class="x-title" :class="{disabled}">
        <img :src="require(`Logos/${logo}.png`)" height="24" class="md-image">
        <div class="text"><slot /></div>
    </div>
</template>

<script>
    export default {
        name: 'x-title',
        props: {
            logo: String,
            disabled: Boolean
        }
    }
</script>

<style lang="scss">
    .x-title {
        display: flex;
        align-items: center;

        .text {
            margin-left: 12px;
            white-space: nowrap;
        }
        &.disabled {
            .md-image {
                opacity: 0.6;
            }
            .text {
                color: $grey-3;
            }
        }
    }
</style>