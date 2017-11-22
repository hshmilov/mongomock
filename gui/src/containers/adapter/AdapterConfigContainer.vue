<template>
    <scrollable-page :title="`adapters > ${adapterData.name}`">
        <card title="configure">
            <template slot="cardContent">
                <svg-icon name="navigation/device" width="24" height="24" :original="true"></svg-icon>
                <div>
                    <!-- Container for list of configured servers - both enabled and disabled -->

                </div>
                <div>
                    <!-- Container for configuration of a single selected \ added server -->

                </div>
                <div class="row">
                    <div class="form-group place-right">
                        <a class="btn btn-inverse" @click="returnToAdapters">cancel</a>
                        <a class="btn" @click="saveAdapter">save</a>
                    </div>
                </div>
            </template>
        </card>
    </scrollable-page>
</template>

<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
    import '../../components/icons/navigation'

	import { mapState, mapGetters, mapActions } from 'vuex'

	export default {
		name: 'adapter-config-container',
        components: {ScrollablePage, Card},
        computed: {
            ...mapState([ 'adapter' ]),
            adapterData() {
            	return this.adapter.currentAdapter.data
            }
        },
        methods: {
			returnToAdapters() {
				this.$router.push({name: 'Adapter'})
            },
            saveAdapter() {
				/* Validation */

				/* Save and return to adapters page */
				this.returnToAdapters()
            }
        },
        created() {

        }
	}
</script>

<style lang="scss">

</style>