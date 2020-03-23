package internal

import "github.com/iancoleman/strcase"

func StringInSlice(a string, list []string) bool {
	for _, b := range list {
		if b == a {
			return true
		}
	}
	return false
}

func SnakeCaseAll(ss []string) []string {
	nss := make([]string, len(ss))
	for i, s := range ss {
		nss[i] = strcase.ToSnake(s)
	}
	return nss
}
