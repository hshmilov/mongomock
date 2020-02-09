const mergedData = (data, schema) => {
  const isSubsetValue = (subsetValue, supersetValue) => {
    if (typeof (subsetValue) !== typeof (supersetValue)) return false;
    if (Array.isArray(subsetValue)) {
      if (subsetValue.length > supersetValue.length) return false;
      for (let i = 0; i < subsetValue.length; i += 1) {
        let found = false;
        supersetValue.forEach((supersetItem) => {
          if (isSubsetValue(subsetValue[i], supersetItem)) found = true;
        });
        if (!found) return false;
      }
      return true;
    }
    if (typeof (subsetValue) === 'object') {
      // eslint-disable-next-line no-use-before-define
      return isSubset(subsetValue, supersetValue);
    }
    return (subsetValue === supersetValue);
  };

  const isSubset = (subset, superset) => {
    let result = true;
    Object.entries(subset).forEach(([key, value]) => {
      if (!result || (value && !superset[key]) || !isSubsetValue(value, superset[key])) {
        result = false;
      }
    });
    return result;
  };
  // returns a "merged" version of the data:
  // "if a row is a full subset of another row, do not show it"
  const localData = [...data];
  const totalExcludedSet = new Set();
  const stringFields = schema.items.filter((x) => x.type === 'string' && !x.name.includes('.'));

  // out of all fields, on the topmost level, which are scalars (specifically a string)
  // those that are unique (and non-null) are never a superset or a subset of any other row
  // this code will find those unique ones and add them to 'totalExcludedSet', so they will
  // not take place in the rest of the algorithm.
  // this is O(n)
  stringFields.forEach((schemaItem) => {
    const fieldName = schemaItem.name;

    const excludedSet = {};
    const valuesSet = new Set();

    localData.map((d) => d[fieldName]).forEach((dataItem, index) => {
      if (!dataItem) return;

      if (valuesSet.has(dataItem)) {
        delete excludedSet[dataItem];
      } else {
        excludedSet[dataItem] = index;
        valuesSet.add(dataItem);
      }
    });

    Object.values(excludedSet).forEach((x) => totalExcludedSet.add(x));
  });

  // over all scalars (strings...) fields,
  // group all values of the same value (and not null) and for each group that has over 1
  // value, try to see if the whole row is also a subset or a superset,
  // and if it does, mark them.
  // This reduces the amount of checks we do later.
  // This is O(n^2) where (n) is the maximal amount of identical values.
  stringFields.forEach((schemaItem) => {
    const fieldName = schemaItem.name;
    const d = {};

    localData.filter((x) => x !== undefined)
      .map((val) => val[fieldName])
      .forEach((dataItem, index) => {
        if (totalExcludedSet.has(index)) return;
        if (!dataItem) return;

        if (d[dataItem]) {
          d[dataItem].push(index);
        } else {
          d[dataItem] = [index];
        }
      });

    Object.values(d).forEach((list) => {
      if (list.length < 2) return;

      for (let i = 0; i < list.length; i += 1) {
        for (let j = 0; j < i; j += 1) {
          if (!(!localData[i] || !localData[j])) {
            if (isSubset(localData[i], localData[j])) {
              localData[i] = undefined;
            } else if (isSubset(localData[j], localData[i])) {
              localData[j] = undefined;
            }
          }
        }
      }
    });
  });

  // this is the lousy part of this algorithm, it is in O(n^2)
  // where (n) = amount of row - amount of rows eliminated in previous steps
  // Goes over any unique pair and check if one is a subset of the other, and if it is,
  // hide show the subset.
  const result = Array.from(totalExcludedSet).map((index) => localData[index]);
  localData.forEach((x, index) => {
    if (x === undefined || totalExcludedSet.has(index)) return;

    let found = false;
    for (let i = 0; i < result.length; i += 1) {
      if (isSubset(result[i], x)) {
        result[i] = x;
        found = true;
        break;
      } else if (isSubset(x, result[i])) {
        found = true;
        break;
      }
    }
    if (!found) {
      result.push(x);
    }
  });

  return result;
};


export default mergedData;
