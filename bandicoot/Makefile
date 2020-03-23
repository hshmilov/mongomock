SHELL := /bin/bash
SOURCE_FILES ?=./...
TEST_PATTERN ?=.
TEST_OPTIONS ?=
.DEFAULT_GOAL := help

PROJECTNAME=$(basename "$(PWD)")
VERSION ?= $(shell git describe --tags)
BUILD := $(shell git rev-parse --short HEAD)
PROJECTNAME := $(basename "$(PWD)")

# Go related variables.
GOBASE=$(PWD)
GOPATH=$(GOBASE)/vendor:$(GOBASE)
GOBIN=$(GOBASE)/bin
GO_FILES := $(shell find . '(' -path '*/.*' -o -path './vendor' -o -name '*_gen.go' ')' -prune -o -name '*.go' -print | cut -b3-)

# colors
CYAN    := \033[96m
RED     := \033[91m
YELLOW	:= \033[93m
GREEN   := \033[92m
RESET	:= \033[0m


## Install all the build and lint dependencies
setup:
	curl -sfL https://install.goreleaser.com/github.com/golangci/golangci-lint.sh | sh
	curl -L https://git.io/misspell | sh
	go mod tidy
.PHONY: setup

## Run all the linters
lint: $(GOLINT) $(STATICCHECK)
	@rm -rf lint.log
	@echo -e "${GREEN}Running gofmt...${RESET}"
	@gofmt $(GO_FILES) 2>&1 | tee lint.log
	@echo -e "${GREEN}Running go vet...${RESET}"
	@go vet $(GO_FILES) 2>&1 | tee -a lint.log
	@echo -e "${GREEN}Running golint...${RESET}"
	./bin/golangci-lint run ./...
	@[ ! -s lint.log ]
.PHONY: lint

## Clean go.mod
go-mod-tidy:
	@go mod tidy -v
	@git diff HEAD
	@git diff-index --quiet HEAD
.PHONY: go-mod-tidy

## Run all the tests
test:
	LC_ALL=C go test $(TEST_OPTIONS) -failfast -race -coverpkg=./... -covermode=atomic -coverprofile=coverage.txt $(SOURCE_FILES) -run $(TEST_PATTERN) -timeout=2m
.PHONY: test

## Run all the tests and opens the coverage report
cover: test
	go tool cover -html=coverage.txt
.PHONY: cover

## Run go-vet on the files in this project
vet:
	go vet -atomic -bool -copylocks -nilfunc -printf -rangeloops -unreachable -unsafeptr -unusedresult .
.PHONY: vet

## serve starts an API server
serve:
	go run . api
.PHONY: serve

## generate filters and graphql API
generate:
	cd ./pkg/gql && go run bandicoot/cmd/sqlgen generate
.PHONY: generate

## builds a bandicoot docker file
docker: generate
	docker build -t bandicoot_base:$(VERSION) .
.PHONY: docker

## builds a postgres docker file (use VERSION=latest if you want rebuild for docker-compose)
postgres:
	cd deployments/docker/postgres && docker build -t axonius_postgres:$(VERSION) .
.PHONY: postgres

## Bench tests server with queries.graphql
bench:
	cat bench.yaml | docker run -i --network=axonius --rm -p 8050:8050 -v /Users/ron/Projects/cortex/bandicoot/api/bench:/graphql-bench/ws/ hasura/graphql-bench:v0.3
.PHONY: bench
# Max target length
TARGET_MAX_CHAR_NUM=20
## Help of all available commands
help:
	@echo -e ''
	@echo 'Usage:'
	@echo -e '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo -e 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  ${YELLOW}%-$(TARGET_MAX_CHAR_NUM)s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)