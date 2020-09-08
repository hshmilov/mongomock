import _isNil from 'lodash/isNil';

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
 * @returns {number} index from server, if exists, or the index of the current iteration
 */
export function getItemIndex(index, item) {
  return _isNil(item.index_in_config) ? index : item.index_in_config;
}

export function getLegendItemColorClass(index, item) {
  const configIndex = getItemIndex(index, item);
  let classname;
  if (this.data.length === 2 && configIndex === 1 && this.data[0].remainder) {
    classname = getDynamicEntryColouringClass(item.portion);
  } else if (item.intersection) {
    classname = getIntersectingEntryColouringClass(configIndex);
  } else {
    classname = getRegularEntryColouringClass(configIndex);
  }
  return classname;
}

export function getRemainderSliceLabel(item) {
  if (item.name === 'ALL') {
    return `Remainder of all ${item.module}`;
  }
  return `Remainder of: ${item.name}`;
}

export function getTotalResultsTitle(total, range, name) {
  return `${range[0]} - ${range[1]} of ${total} ${name}`;
}
