import Vue from 'vue'
import { gettingStarted } from './index.stories';
import XMilestone from '../src/components/networks/getting-started/Milestone.vue'

Vue.component('x-milestone', XMilestone);

const container = () => {
    return {
        template: '<div style="width: 400px;"><story/></div>',
    };
};
gettingStarted.addDecorator(container).add('Milestone - not completed', 
    () => ({
        template: `<x-milestone 
        title="Lurem Ipsum" 
        description="Vue will automatically sniff whether the target element has CSS transitions or animations applied. If it does, CSS transition classes will be added/removed at appropriate timings."
        link="https://www.google.com"
        path="devices"
        />`
    })
)

gettingStarted.add('Milestone - completed', () => ({
    template: `<x-milestone 
    completed
    title="Lurem Ipsum" 
    description="Vue will automatically sniff whether the target element has CSS transitions or animations applied. If it does, CSS transition classes will be added/removed at appropriate timings."
    link="https://www.google.com"
    path="devices"
    />`
}))

gettingStarted.add('Milestone - no link', () => ({
    template: `<x-milestone 
    title="Lurem Ipsum" 
    description="Vue will automatically sniff whether the target element has CSS transitions or animations applied. If it does, CSS transition classes will be added/removed at appropriate timings."
    path="devices"
    />`
}))

gettingStarted.add('Milestone - no description', () => ({
    template: `<x-milestone 
    title="Lurem Ipsum" 
    path="devices"
    />`
}))

gettingStarted.add('Milestone - not interactive action', () => ({
    template: `<x-milestone 
    title="Lurem Ipsum" 
    description="Vue will automatically sniff whether the target element has CSS transitions or animations applied. If it does, CSS transition classes will be added/removed at appropriate timings."
    path="devices"
    :interactive="false"
    />`
}))