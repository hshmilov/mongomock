import Vue from 'vue';
import { storiesOf } from '@storybook/vue';
import { withKnobs, text, boolean } from '@storybook/addon-knobs';


export const storiesOfAxons = storiesOf('Axons Playground', module);
export const gettingStarted = storiesOf('Getting Started', module);


storiesOfAxons.addDecorator(withKnobs);