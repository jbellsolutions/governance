.PHONY: build test lint install clean

build:
	go build -o bin/gov-pp-cli ./cmd/gov-pp-cli

test:
	go test ./...

lint:
	golangci-lint run

install:
	go install ./cmd/gov-pp-cli

clean:
	rm -rf bin/

build-mcp:
	go build -o bin/gov-pp-mcp ./cmd/gov-pp-mcp

install-mcp:
	go install ./cmd/gov-pp-mcp

build-all: build build-mcp
