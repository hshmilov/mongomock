import _find from 'lodash/find';
import _matchesProperty from 'lodash/matchesProperty';
import _get from 'lodash/get';

import { getTypeFromField } from '@constants/utils';
import { INCLUDE_OUDATED_MAGIC, validateBrackets } from '@constants/filter';
import Expression from './expression';
import Condition from './condition';

/**
 * Builds the query filter from the expressions list and the meta data
 * @param {array} schema - the schema of the fields in this module
 * @param {array} expressions - the expressions from the query wizard
 * @param {object} meta - data that describe special attributes of this query
 * @param {string} prevExpressionsQuery - the previous valid calculated filter of the expressions
 * @returns {{compileQuery: (function(*=, *=): string)}}
 * @constructor
 */
const QueryBuilder = (schema, expressions, meta, prevExpressionsQuery) => {
  const errors = [];

  const compileCondition = (childExpression, fieldSchema) => {
    const conditionCalculator = Condition(
      childExpression.field,
      fieldSchema,
      childExpression.fieldType,
      childExpression.compOp,
      childExpression.value,
      childExpression.filteredAdapters,
      childExpression.not,
    );
    const conditionError = conditionCalculator.formatCondition();
    if (conditionError) {
      throw conditionError;
    }
    return !childExpression.context ? conditionCalculator.composeCondition() : '';
  };

  const addFilterOutExpression = (otherFilters) => {
    const { fields } = _find(schema, _matchesProperty('name', meta.filterOutExpression.fieldType));
    const fieldSchema = _find(fields, _matchesProperty('name', meta.filterOutExpression.field));
    // we compile the same expression as a condition
    // and as a expression later on, remove the duplicate 'not' in the final filter
    const filterOutCondition = { ...meta.filterOutExpression, not: undefined };
    const filterOutConditionFilter = compileCondition(filterOutCondition, fieldSchema);

    const filterOutFilter = Expression(
      meta.filterOutExpression,
      filterOutConditionFilter,
      true,
    ).compileExpression().filter;

    let filter = '';
    if (otherFilters.trim() !== '') {
      filter = `${filterOutFilter} and (${otherFilters})`;
    } else {
      filter = filterOutFilter;
    }
    return filter;
  };

  /**
   * Compiles the whole query into a single string filter
   * @returns {{}} - the string filter
   */
  const compileQuery = (recompile = true) => {
    if (!expressions) {
      return {};
    }
    const filters = [];
    const bracketWeights = [];
    expressions.forEach((expression, index) => {
      if (recompile) {
        if (!expression.field
          || (!expression.compOp && !expression.context && expression.field !== 'saved_query')) {
          return;
        }

        if (expression.error) {
          errors.push((expression.error));
          return;
        }
        if (!expression.fieldType) {
          expression.fieldType = getTypeFromField(expression.field);
        }
        const { fields } = _find(schema, _matchesProperty('name', expression.fieldType));
        const fieldSchema = _find(fields, _matchesProperty('name', expression.field));
        let compiledFilter = '';
        try {
          // we compile the same expression as a condition
          // and as a expression later on, remove the duplicate 'not' in the final filter
          const condition = { ...expression, not: undefined };
          compiledFilter = compileCondition(condition, fieldSchema);
        } catch (error) {
          errors.push(error);
          if (expression.filter) {
            filters.push(expression.filter);
            bracketWeights.push(expression.bracketWeight);
          }
          return;
        }
        if (expression.context) {
          if (expression.context === 'OBJ') {
            expression.children.forEach((child) => {
              if (child.expression.field) {
                const childFieldSchema = _find(fieldSchema.items.items, _matchesProperty('name', child.expression.field));
                child.condition = compileCondition(child.expression, childFieldSchema);
              } else {
                child.condition = '';
              }
            });
          } else {
            expression.children.forEach((child) => {
              const childField = _get(child, 'expression.field');
              if (childField) {
                const adapterSchema = fields.find((field) => field.name === childField);
                const childFieldCompileName = childField.replace(`adapters_data.${expression.field}`, 'data');
                child.condition = compileCondition({
                  ...child.expression, field: childFieldCompileName,
                }, {
                  ...adapterSchema, name: childFieldCompileName,
                });
              } else {
                child.condition = '';
              }
            });
          }
        }

        const expressionResult = Expression(
          expression,
          compiledFilter,
          index === 0,
        ).compileExpression();
        if (expressionResult.error) {
          errors.push(expressionResult.error);
          return;
        }
        expression.filter = expressionResult.filter;
        expression.bracketWeight = expressionResult.bracketWeight;
        filters.push(expressionResult.filter);
        bracketWeights.push(expressionResult.bracketWeight);
      } else if (expression.filter) {
        filters.push(expression.filter);
        bracketWeights.push(expression.bracketWeight);
      }
    });
    let filter = '';
    let onlyExpressionsFilter = filters.join(' ');

    const bracketsError = validateBrackets(bracketWeights);
    if (bracketsError) {
      errors.push(bracketsError);
      onlyExpressionsFilter = prevExpressionsQuery;
    }
    if (meta
      && meta.filterOutExpression
      && meta.filterOutExpression.value
      && !meta.filterOutExpression.showIds) {
      filter = addFilterOutExpression(onlyExpressionsFilter);
    } else {
      filter = onlyExpressionsFilter;
    }

    if (filter && meta && meta.uniqueAdapters) {
      filter = `${INCLUDE_OUDATED_MAGIC}${filter}`;
    }

    if (meta && meta.enforcementFilter && filter.indexOf(meta.enforcementFilter) === -1) {
      filter = `${meta.enforcementFilter} ${filter}`;
    }
    return {
      resultFilter: filter,
      onlyExpressionsFilter,
    };
  };

  const getError = () => {
    if (errors.length > 0) {
      return errors[0];
    }
    return '';
  };

  return {
    compileQuery,
    getError,
  };
};

export default QueryBuilder;
