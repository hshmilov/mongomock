import { Icon as AIcon } from 'ant-design-vue';
import _prop from 'lodash/property';
import _omit from 'lodash/omit';
import _set from 'lodash/set';
import navigation from './navigation';
import custom from './custom';
import symbol from './symbol';
import illustration from './illustration';
import action from './action';
import logo from './logo';

const categories = {
  navigation,
  custom,
  symbol,
  logo,
  illustration,
  action,
};

export default {
  name: 'XIcon',
  components: { AIcon },
  props: {
    ...AIcon.props,
    family: {
      type: String,
      default: '',
    },
  },
  methods: {
    getCustomSVGIcon(family, type) {
      const svgIconLense = _prop(`${family}.${type}`);
      return svgIconLense(categories);
    },
  },
  render() {
    let props = { ...this.$props };
    if (this.family) {
      props = _omit(props, 'type');
      _set(props, 'component', this.getCustomSVGIcon(this.family, this.type));
    }
    return <AIcon { ...{ props } } class="x-icon"/>;
  },
};
