import _matches from 'lodash/matches';

import { getExcludedAdaptersFilter } from '../constants/utils';
import { filterOutExpression, expression as emptyExpression } from '../constants/filter';

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
    if (!expression.field || (expression.context && !childExpressionCond())) {
      return { filter: '', bracketWeight: 0 };
    }
    const error = checkErrors();
    if (error) {
      return { error };
    }

    const filterStack = [];

    if (expression.logicOp && !isFirst) {
      filterStack.push(`${expression.logicOp} `);
    }

    let bracketWeight = 0;
    if (expression.leftBracket) {
      filterStack.push('(');
      bracketWeight -= 1;
    }
    if (expression.not) {
      filterStack.push('not ');
    }
    if (expression.context) {
      if (expression.context === 'OBJ') {
        const childExpression = getMatchExpression(expression.field, childExpressionCond());
        filterStack.push('({val})'.replace(/{val}/g, getExcludedAdaptersFilter(expression.fieldType,
          expression.field, expression.filteredAdapters, childExpression)));
      } else {
        const adapterChildExpression = `plugin_name == '${expression.field}' and ${childExpressionCond()}`;
        filterStack.push(getMatchExpression('specific_data', adapterChildExpression));
      }
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
