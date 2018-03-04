<template>
    <div>
        <div v-for="item in data" class="counter">
            <div class="count" :class="{highlight: item.highlight}">{{ item.count }}</div>
            <div class="title">{{ item.title }}</div>
        </div>
    </div>
</template>

<script>
	export default {
		name: 'x-counter',
        props: { data: {required: true}}
	}
</script>

<style lang="scss" scoped>
    @import '../../scss/config';

    .counter {
        .count {
            font-size: 72px;
            display: inline;
            color: $blue;
            &.highlight {
                color: $orange;
            }
        }
        .title {
            display: inline-block;
            max-width: 180px;
            text-align: left;
            line-height: 36px;
            margin-left: 12px;
        }
    }
</style>