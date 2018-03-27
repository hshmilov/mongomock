<template>
    <div class="results x-grid x-grid-col-2">
        <template v-for="name, index in Object.keys(data)">
            <div class="title">{{ name }}</div>
            <div class="count">{{ data[name] }}</div>
        </template>
    </div>
</template>

<script>
	export default {
		name: 'x-results-chart',
        props: {data: {required: true}}
	}
</script>

<style lang="scss" scoped>
    @for $i from 1 through length($extra-colours) {
        .count:nth-child(#{$i * 2}) {
            color: nth($extra-colours, $i);
        }
    }

    .results {
        font-size: 20px;
        &.x-grid-col-2 {
            grid-template-columns: 2fr 1fr;
        }
        .title {
            font-weight: 300;
        }
        .count {
            text-align: center;
        }
    }
</style>