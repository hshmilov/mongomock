import _find from 'lodash/find'
import _matchesProperty from 'lodash/matchesProperty'

import {INCLUDE_OUDATED_MAGIC} from '../constants/filter'
import Expression from "./expression";
import Condition from "./condition";

/**
 * Builds the query filter from the expressions list and the meta data
 * @param {array} schema - the schema of the fields in this module
 * @param {array} expressions - the expressions from the query wizard
 * @param {object} meta - data that describe special attributes of this query
 * @param {string} prevExpressionsQuery - the previous valid calculated filter of the expressions
 * @returns {{compileQuery: (function(*=, *=): string)}}
 * @constructor
 */
const QueryBuilder = function(schema, expressions, meta, prevExpressionsQuery) {
    let errors = []
    /**
     * Compiles the whole query into a single string filter
     * @returns {string} - the string filter
     */
    const compileQuery = (recompile = true) => {
        let filters = []
        let bracketWeights = []
        expressions.forEach((expression, index) => {
            if(recompile) {
                if (!expression.fieldType ||
                  !expression.field ||
                  (!expression.compOp && !expression.obj && expression.field !== 'saved_query')) {
                    return
                }

                if (expression.error) {
                    errors.push((expression.error))
                    return
                }
                let fields = _find(schema, _matchesProperty('name', expression.fieldType)).fields
                let fieldSchema = _find(fields, _matchesProperty('name', expression.field))
                let compiledFilter = ''
                try {
                    compiledFilter = compileCondition(expression, fieldSchema)
                } catch (error) {
                    errors.push(error)
                    if(expression.filter){
                        filters.push(expression.filter)
                        bracketWeights.push(expression.bracketWeight)
                    }
                    return
                }

                if (expression.obj) {
                    expression.nested.forEach(nestedExpression => {
                        if (nestedExpression.expression.field) {
                            let nestedFieldSchema = _find(fieldSchema.items.items, _matchesProperty('name', nestedExpression.expression.field))
                            nestedExpression.condition = compileCondition(nestedExpression.expression, nestedFieldSchema)
                        } else {
                            nestedExpression.condition = ''
                        }
                    })
                }

                let expressionResult = Expression(
                  expression,
                  compiledFilter,
                  index === 0).compileExpression()
                if (expressionResult.error) {
                    errors.push(expressionResult.error)
                    return
                }
                expression.filter = expressionResult.filter
                expression.bracketWeight = expressionResult.bracketWeight
                filters.push(expressionResult.filter)
                bracketWeights.push(expressionResult.bracketWeight)
            } else {
                if(expression.filter) {
                    filters.push(expression.filter)
                    bracketWeights.push(expression.bracketWeight)
                }
            }


        })

        let filter = ''
        let onlyExpressionsFilter = filters.join(' ')

        let bracketsError = validateBrackets(bracketWeights)
        if(bracketsError){
            errors.push(bracketsError)
            onlyExpressionsFilter = prevExpressionsQuery
        }

        if(meta && meta.filterOutExpression && meta.filterOutExpression.value && !meta.filterOutExpression.showIds){
            filter = addFilterOutExpression(onlyExpressionsFilter)

        } else {
            filter = onlyExpressionsFilter
        }

        if(meta && meta.uniqueAdapters) {
            filter = `${INCLUDE_OUDATED_MAGIC}${filter}`
        }

        if(meta && meta.enforcementFilter && filter.indexOf(meta.enforcementFilter) === -1){
            filter = `${meta.enforcementFilter} ${filter}`
        }
        return {
            resultFilter: filter,
            onlyExpressionsFilter: onlyExpressionsFilter
        }
    }

    const addFilterOutExpression = (otherFilters) => {
        let fields = _find(schema, _matchesProperty('name', meta.filterOutExpression.fieldType)).fields
        let fieldSchema = _find(fields, _matchesProperty('name', meta.filterOutExpression.field))
        let filterOutConditionFilter = compileCondition(meta.filterOutExpression, fieldSchema)

        let filterOutFilter = Expression(
          meta.filterOutExpression,
          filterOutConditionFilter,
          true).compileExpression().filter

        let filter = ''
        if (otherFilters.trim() !== '') {
            filter = `${filterOutFilter} and (${otherFilters})`
        } else {
            filter = filterOutFilter
        }
        return filter
    }

    const compileCondition = (expression, fieldSchema) => {
        let conditionCalculator = Condition(
            expression.field,
            fieldSchema,
            expression.fieldType,
            expression.compOp,
            expression.value,
            expression.filteredAdapters,
            meta ? meta.uniqueAdapters : false
        )
        let conditionError = conditionCalculator.formatCondition()
        if(conditionError){
            throw conditionError
        }

        return !expression.obj ? conditionCalculator.composeCondition() : ''
    }

    const getError = () => {
        if(errors.length > 0){
            return errors[0]
        }
        return ''
    }

    return {
        compileQuery,
        getError
    }
}

const validateBrackets = (bracketWeights) => {
    let totalBrackets = bracketWeights.reduce((accumulator, currentVal) => accumulator + currentVal, 0)
    if (totalBrackets !== 0) {
        return (totalBrackets < 0) ? 'Missing right bracket' : 'Missing left bracket'
    }
    return ''
}

export default QueryBuilder
