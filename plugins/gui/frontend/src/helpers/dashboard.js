import { ChartTypesEnum } from '@constants/dashboard';

export const getRegularEntryColouringClass = (index) => {
  // there are only 10 possible colors
  const colorIndex = (index % 10) + 1;
  return `pie-fill-${colorIndex}`;
};

export const getDynamicEntryColouringClass = (portion) => `indicator-fill-${Math.ceil(portion * 4)}`;

export const getIntersectingEntryColouringClass = (index) => {
  // there are only 10 possible colors
  const colorIndex = (index % 10) + 1;
  return `fill-intersection-${colorIndex - 1}-${colorIndex}`;
};

/**
 * we apply legend colors based on indices.
 * dataItems order might changed based on sorting and few other reasons.
 * @returns {number} if n < 0, user the index of the current itteration
 */
export function getItemIndex(item, chartMetric) {
  let n = -1;
  if (chartMetric === ChartTypesEnum.compare) {
    n = item.index_in_config;
  } else if (chartMetric === ChartTypesEnum.intersect) {
    const allEntriesNamesBesidesIntersecting = this.data.filter((entry) => !entry.intersection).map((entry) => entry.name);
    n = allEntriesNamesBesidesIntersecting.indexOf(item.name);
  }
  return n;
}

export function getLegendItemColorClass(index, item) {
  let classname;
  if (this.data.length === 2 && index === 1 && this.data[0].remainder) {
    classname = getDynamicEntryColouringClass(item.portion);
  } else if (item.intersection) {
    classname = getIntersectingEntryColouringClass(index);
  } else {
    classname = getRegularEntryColouringClass(index);
  }
  return classname;
}

export function getRemainderSliceLabel(item) {
  if (item.name === 'ALL') {
    return `Remainder of all ${item.module}`;
  }
  return `Remainder of: ${item.name}`;
}
