package sql

import (
	"bandicoot/internal/sqlgen"
	"context"
	"encoding/json"
	"fmt"
	"github.com/rs/zerolog"
	"github.com/spf13/afero"
	"github.com/stretchr/testify/assert"
	"github.com/vektah/gqlparser/v2"
	"github.com/vektah/gqlparser/v2/ast"
	"testing"
)

func TestTranslator_Translate(t *testing.T) {
	l := zerolog.Nop()
	for _, tc := range translationTestCases {
		data, err := afero.ReadFile(afero.NewOsFs(), tc.schema)
		assert.Nil(t, err)
		schema := gqlparser.MustLoadSchema(&ast.Source{Input: string(data)})
		var i = 0
		cfg := sqlgen.Config{
			Schema: schema,
			GenerateTableName: func(_ int) string {
				i++
				return fmt.Sprintf("sq%d", i)
			},
			BeforeTranslation: nil,
			BeforeClauses:     nil,
		}
		variables := make(map[string]interface{})
		if tc.variables != "" {
			err := json.Unmarshal([]byte(tc.variables), &variables)
			assert.Nil(t, err, tc.name)
		}
		translator := CreateTranslator(context.Background(), cfg, variables, nil, &l)
		q, err := gqlparser.LoadQuery(schema, tc.query)
		assert.Nil(t, err)
		op := q.Operations.ForName("")
		field := op.SelectionSet[0].(*ast.Field)
		r, _ := translator.Translate(field)
		assert.Equal(t, r.Query, tc.wantQuery)
		assert.EqualValues(t, r.Params, tc.wantParams)
	}
}

func BenchmarkTranslator_TranslateSimple(b *testing.B) {
	benchmarkTranslatorTranslate(translationTestCases[0], b)
}

func BenchmarkTranslator_TranslateOneRelation(b *testing.B) {
	benchmarkTranslatorTranslate(translationTestCases[3], b)
}

func BenchmarkTranslator_TranslateComplex(b *testing.B) {
	benchmarkTranslatorTranslate(translationTestCases[4], b)
}

func benchmarkTranslatorTranslate(u translationTestCase, b *testing.B) {
	data, err := afero.ReadFile(afero.NewOsFs(), u.schema)
	assert.Nil(b, err)
	schema := gqlparser.MustLoadSchema(&ast.Source{Input: string(data)})
	q, err := gqlparser.LoadQuery(schema, u.query)
	assert.Nil(b, err)
	l := zerolog.Nop()
	op := q.Operations.ForName("")
	field := op.SelectionSet[0].(*ast.Field)
	cfg := sqlgen.Config{Schema: schema}
	variables := make(map[string]interface{})
	if u.variables != "" {
		err := json.Unmarshal([]byte(u.variables), &variables)
		assert.Nil(b, err)
	}
	for n := 0; n < b.N; n++ {
		_, _ = CreateTranslator(context.Background(), cfg, variables, nil, &l).Translate(field)
	}
}
