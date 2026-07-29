.PHONY: test test-app test-cli test-web build build-app build-cli build-web run-db stop-db run-app run-app-memory run-web local-up local-down

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

test: test-app test-cli test-web

test-app:
	cd "$(ROOT)/app" && go test ./...

test-cli:
	cd "$(ROOT)/cli" && go test ./...

test-web:
	cd "$(ROOT)/web" && npm run check

build: build-app build-cli build-web

build-app:
	mkdir -p "$(ROOT)/bin"
	cd "$(ROOT)/app" && go build -o "$(ROOT)/bin/mycasapro-server" ./cmd/server

build-cli:
	mkdir -p "$(ROOT)/bin"
	cd "$(ROOT)/cli" && go build -o "$(ROOT)/bin/mycasapro" ./cmd/mycasapro

build-web:
	cd "$(ROOT)/web" && npm run build

run-db:
	docker compose -f "$(ROOT)/infra/docker-compose.postgres.yml" up -d

stop-db:
	docker compose -f "$(ROOT)/infra/docker-compose.postgres.yml" down

run-app:
	APP_ADDR=:8081 APP_WEB_URL=http://localhost:3000 APP_STORE_BACKEND=postgres APP_DATABASE_URL=postgres://mycasapro:mycasapro_local@localhost:5432/mycasapro?sslmode=disable APP_AUTO_MIGRATE=true go run "$(ROOT)/app/cmd/server"

run-app-memory:
	APP_ADDR=:8081 APP_WEB_URL=http://localhost:3000 APP_STORE_BACKEND=memory go run "$(ROOT)/app/cmd/server"

run-web:
	cd "$(ROOT)/web" && npm run dev

local-up:
	docker compose -f "$(ROOT)/infra/docker-compose.local-build.yml" up --build -d

local-down:
	docker compose -f "$(ROOT)/infra/docker-compose.local-build.yml" down
