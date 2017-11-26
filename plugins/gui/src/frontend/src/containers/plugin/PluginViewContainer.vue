<template>
    <scrollable-page v-bind:title="'Plugins > ' + $route.params.id + ' Plugin'">

    <div class="row"  style="height: 100vh">
        <div class="col-md-6">
        
            <div class="card">
                <div class="card-header">
                    <span class="card-header-title">Plugin Configuration</span>
                </div>
                <div class="card-body"  style="height: 80vh">
                    <h1 style="margin-bottom: 16px; color: #4796e4"><img src="/api/gui/src/assets/images/general/about.png" style="height: 40px; margin-right: 8px;"/> About</h1>
                    {{ currentPlugin['description'] }}
                    <br><br><br>
                    <hr>

                    <h1 style="margin-bottom: 16px; color: #4796e4"><img src="/api/gui/src/assets/images/general/settings.png" style="height: 40px; margin-right: 8px;"/> Settings</h1>
                    The following settings affect the behavior of the {{ currentPlugin['name'] }} plugin.
                    <br><br>
                    Plugin State: &nbsp;&nbsp;
                    <toggle-button @change="togglebutton" v-model="plugin_state"
                                   :color="{checked: '#70AE58', unchecked: '#CCCCCC'}"
                                   :sync="true"
                                   :labels="true"></toggle-button>
                    <br>
                    Time until a device is blocked: &nbsp; <input class="form-control" style="width: 80px; display: inline-block" v-model="ttl" placeholder="0">
                    hours.<br>
                    <a href="#" class="btn" style="position:absolute; right: 10px; bottom: 10px;background-color: #4796e4; color: white; text-align: right; display: block" v-on:click="save">Save</a>
                </div>
            </div>

        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <span class="card-header-title">Results</span>
                </div>
                <div class="card-body"  style="height: 80vh">
                    <h1 style="color: #4796e4"><img src="/api/gui/src/assets/images/general/results.png" style="height: 40px; margin-right: 8px;"/> Results</h1>
                    <vue-chart style="height: 100%"
                            chart-type="PieChart"
                            :columns="[{'type': 'string', 'label': 'haha'}, {'type': 'number', 'label': 'hihi'}]"
                            :rows=this.rows
                            :options="{
                        title: 'QCore Devices Blocked',
                        is3D: true,
                        height: 400,
                        curveType: 'function',
                        colors: ['#ffb22b', '#26dad2', '#f3b49f', '#f6c7b6']
                    }"
                    ></vue-chart>
                </div>
            </div>

        </div>
    </div>
        
    </scrollable-page>
</template>


<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import ScrollableTable from '../../components/ScrollableTable.vue'
    import Card from '../../components/Card.vue'
    import ToggleButton from 'vue-js-toggle-button'
    import VueCharts from 'vue-charts'
    import Vue from 'vue'
    import axios from 'axios'

    Vue.use(ToggleButton)
    Vue.use(VueCharts)

    import {mapState, mapGetters, mapActions} from 'vuex'

    export default {
        name: 'plugins-view-container',
        components: {ScrollablePage, ScrollableTable, Card},
        data: function () {
            return {
                "ttl": null,
                "plugin_state": false,
                "rows": []
            }
        },
        computed: {
            currentPlugin() {
                for (var i in this.plugin.pluginList.data) {
                    var d = this.plugin.pluginList.data[i]
                    if (d['name'] === this.$route.params.id) {
                        return d
                    }
                }
            },
            ...mapState(['plugin'])
        },
        created: function () {
           this.flushall()
        },
        methods: {
            save: function () {
                axios.post(`http://localhost:1337/api/plugins/${this.$route.params.id}`, {'time_to_die': this.ttl, 'plugin_state': this.plugin_state}).then(({data}) => {
                this.flushall()
                });
            },
            togglebutton: function (data) {
                if (data.value == true) {
                    //axios.get(`http://localhost:1337/api/plugins/${this.$route.params.id}/start`);
                }
                else {
                    //axios.get(`http://localhost:1337/api/plugins/${this.$route.params.id}/stop`);
                }
            },
            flushall: function() {
                axios.get(`http://localhost:1337/api/plugins/${this.$route.params.id}`).then(({data}) => {
                this.ttl = data.parameters.time_to_die[0];
                this.plugin_state = (data.parameters.plugin_state[0] == true ? true : false);
                this.rows = [];
                for(var x in data.data) {
                    this.rows.push([x, data.data[x]]);
                }
            });
            }
        }
    }
</script>


<style lang="scss">

</style>