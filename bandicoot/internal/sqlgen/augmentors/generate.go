package augmentors

import (
	"fmt"
	"github.com/vektah/gqlparser/v2"
	"github.com/vektah/gqlparser/v2/ast"
	"github.com/vektah/gqlparser/v2/formatter"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// loadSchemaFromPath loads all graphql files from path and builds an ast.Schema
func loadSchemaFromPath(path string) (*ast.Schema, error) {
	fileList := make([]string, 0)
	err := filepath.Walk(path, func(path string, f os.FileInfo, err error) error {
		if f.IsDir() {
			return err
		}
		fileList = append(fileList, path)
		return err
	})
	if err != nil {
		return nil, err
	}
	sources := make([]*ast.Source, 0)
	for _, f := range fileList {

		b, err := ioutil.ReadFile(f)
		if err != nil {
			log.Print(err)
			continue
		}
		sources = append(sources, &ast.Source{Name: f, Input: string(b)})
	}
	// load schema
	s, err := gqlparser.LoadSchema(sources...)
	return s, nil
}

// Generate parses a standard graphQL schema and enhances it with augmenters into an SQLgen graphQL schema
func Generate(input string, output string, augmenters []Augmenter) {
	parsedSchema, err := loadSchemaFromPath(input)
	if err != nil {
		log.Fatalf("Schema parsing failed. Error: %s", err)
	}

	// Iterate over given augmenters allowing them to change the schema
	for _, a := range augmenters {
		if err := a.Schema(parsedSchema); err != nil {
			log.Fatalf("Schema augmentation failed. Error: %s", err)
		}
	}

	// Go over all types in schema and augment them.
	for _, t := range parsedSchema.Types {
		// skip internal types or types that aren't composite (interfaces, objects, unions)
		if strings.HasPrefix(t.Name, "__") || !t.IsCompositeType() {
			continue
		}
		for _, f := range t.Fields {
			// Even in objects some fields might be internal, skip them
			if strings.HasPrefix(f.Name, "__") {
				continue
			}
			for _, a := range augmenters {
				if err := a.Field(parsedSchema, f, t); err != nil {
					log.Fatalf("field augmentation failed. Error: %s", err)
				}
			}
		}
	}

	// Finally save
	o, err := os.Create(output)
	if err != nil {
		log.Fatal(err)
	}
	_, _ = o.WriteString(fmt.Sprintf("# Code generated by go generate; DO NOT EDIT THIS FILE. \n"+
		"# This file was generated at %s\n", time.Now().Format(time.RFC3339)))
	formatter.NewFormatter(o).FormatSchema(parsedSchema)
	// write to file
	defer o.Close()
}
