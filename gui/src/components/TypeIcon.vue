 <template>
    <span>
        <i v-if="value.toLowerCase().indexOf('user') > -1" class="icon-user2"></i>
        ({{ value }})
    </span>
</template>

<script>
	export default {
		name: 'type-icon',
        props: ['value']
	}
</script>

<style lang="scss">

</style>