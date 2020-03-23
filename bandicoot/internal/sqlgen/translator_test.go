package sqlgen

import (
	"fmt"
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestGetComparisonOperation(t *testing.T) {
	name, op := GetComparisonOperation(OperationLogicAnd)
	assert.Equal(t, name, "")
	assert.Equal(t, op, OperationLogicAnd)

	name, op = GetComparisonOperation(OperationLogicOr)
	assert.Equal(t, name, "")
	assert.Equal(t, op, OperationLogicOr)

	name, op = GetComparisonOperation(OperationLogicNot)
	assert.Equal(t, name, "")
	assert.Equal(t, op, OperationLogicNot)

	name, op = GetComparisonOperation(fmt.Sprintf("name_%s", OperationNotIn))
	assert.Equal(t, name, "name")
	assert.Equal(t, op, OperationNotIn)

	name, op = GetComparisonOperation(fmt.Sprintf("name_%s", OperationEq))
	assert.Equal(t, name, "name")
	assert.Equal(t, op, OperationEq)

	name, op = GetComparisonOperation(fmt.Sprintf("name_%s", OperationBoolExp))
	assert.Equal(t, name, "name")
	assert.Equal(t, op, OperationBoolExp)

	name, op = GetComparisonOperation("name_somethingS_something_something")
	assert.Equal(t, name, "name")
	assert.Equal(t, op, "somethingS_something_something")
}
