import _matches from 'lodash/matches';

import { getExcludedAdaptersFilter } from '../constants/utils';
import { filterOutExpression, sizeLtGtFields, expression as emptyExpression } from '../constants/filter';

/**
 * Calculator of a single expression with a single condition or with nested conditions
 * @param {object} expression - the expression attributes
 * @param {string} condition - the condition (compiled into string) if this expression is with a single condition
 * @param {boolean} isFirst - true if this is the first filter of the array
 * @return {{compileExpression: function}}
 * @constructor
 */
const Expression = function (expression, condition, isFirst) {
  /**
     * compiles the expression into a string filter
     * @returns {{error: string}|{filter: string, bracketWeight: number}}
     */
  const compileExpression = () => {
    if (!expression.field || (expression.context && !childExpressionCond() && expression.context !== 'CMP')) {
      return { filter: '', bracketWeight: 0 };
    }
    const error = checkErrors();
    if (error) {
      return { error };
    }

    const filterStack = [];

    if (expression.logicOp && !isFirst) {
      if (expression.context === 'CMP' && (expression.value === '' || (['<Days', '>Days'].includes(expression.compOp) && isNaN(expression.subvalue)))) {

      } else {
        filterStack.push(`${expression.logicOp} `);
      }
    }

    let bracketWeight = 0;
    if (expression.leftBracket) {
      filterStack.push('(');
      bracketWeight -= 1;
    }
    if (expression.not && expression.context !== 'CMP') {
      filterStack.push('not ');
    }
    if (expression.context) {
      if (expression.context === 'OBJ') {
        const childExpression = getMatchExpression(expression.field, childExpressionCond());
        filterStack.push('({val})'.replace(/{val}/g, getExcludedAdaptersFilter(expression.fieldType,
          expression.field, expression.filteredAdapters, childExpression)));
      } else if (expression.context === 'CMP' && expression.value !== '') {
        switch (expression.compOp) {
          case 'equals':
            if (expression.not)
              filterStack.push(`${expression.field} != ${expression.value}`);
            else
              filterStack.push(`${expression.field} == ${expression.value}`);
            break;
          case '>':
            filterStack.push(`${expression.field} > ${expression.value}`);
            break;
          case '<':
            filterStack.push(`${expression.field} < ${expression.value}`);
            break;
          case '>=':
            filterStack.push(`${expression.field} >= ${expression.value}`);
            break;
          case '<=':
            filterStack.push(`${expression.field} <= ${expression.value}`);
            break;
          case '<Days':
            if (!isNaN(expression.subvalue)) filterStack.push(`${expression.field} ${expression.subvalue < 0 ? '-' : '+'} ${expression.subvalue < 0 ? expression.subvalue * -1 : expression.subvalue} ${expression.compOp[0]} ${expression.value}`);
            break;
          case '>Days':
            if (!isNaN(expression.subvalue)) filterStack.push(`${expression.field} ${expression.compOp[0]} ${expression.value} ${expression.subvalue < 0 ? '-' : '+'} ${expression.subvalue < 0 ? expression.subvalue * -1 : expression.subvalue}`);
            break;
        }
      } else if (expression.context !== 'CMP') {
        const adapterChildExpression = `plugin_name == '${expression.field}' and ${childExpressionCond()}`;
        filterStack.push(getMatchExpression('specific_data', adapterChildExpression));
      }
    } else if (sizeLtGtFields.includes(expression.field) && expression.compOp == 'sizegt') {
      if (expression.value >= 0 && expression.value <= 10) {
        filterStack.push(`(((${expression.field} == ({"$exists":true,"$ne":[]})) and ${expression.field} != []) and `);
        for (let i = 0; i <= expression.value; i++) {
          if (i > 0) filterStack.push(' and ');
          filterStack.push(`not ${expression.field} == size(${i})`);
        }
        filterStack.push(')');
      } else {
        return { error: 'Value must be between 0 to 10' };
      }
    } else if (sizeLtGtFields.includes(expression.field) && expression.compOp == 'sizelt') {
      if (expression.value > 0 && expression.value <= 10) {
        filterStack.push(`(not ((${expression.field} == ({"$exists":true,"$ne":[]})) and ${expression.field} != []) or `);
        for (let i = 0; i < expression.value; i++) {
          if (i > 0) filterStack.push(' or ');
          filterStack.push(`${expression.field} == size(${i})`);
        }
        filterStack.push(')');
      } else {
        return { error: 'Value must be between 1 to 10' };
      }
    } else if (expression.field === 'saved_query') {
      filterStack.push(`({{QueryID=${expression.value}}})`);
    } else {
      filterStack.push(condition);
    }
    if (expression.rightBracket) {
      filterStack.push(')');
      bracketWeight += 1;
    }

    return { filter: filterStack.join(''), bracketWeight };
  };

  const checkErrors = () => {
    if (!isFirst && !expression.logicOp) {
      return 'Logical operator is needed to add expression to the filter';
    } if (expression.context && !expression.field) {
      return 'Select an object to add nested conditions';
    }
    return '';
  };

  const childExpressionCond = () => expression.children
    .filter((item) => item.condition)
    .map((item) => item.condition)
    .join(' and ');

  return {
    compileExpression,
  };
};

const getMatchExpression = (field, condition) => `${field} == match([${condition}])`;

export const isFilterOutExpression = (expression) => _matches(filterOutExpression)(expression);

export const isEmptyExpression = (expression) => _matches(emptyExpression)(expression);

export default Expression;
