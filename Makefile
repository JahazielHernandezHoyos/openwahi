DEV_COMPOSE  := docker compose --env-file .env.dev -f docker-compose.dev.yml
PROD_COMPOSE := docker compose --env-file .env.prod -f docker-compose.prod.yml

.PHONY: help dev dev-down dev-logs prod prod-down prod-logs

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

.env.dev:
	@echo "Missing .env.dev — run: cp .env.dev.example .env.dev" && exit 1

.env.prod:
	@echo "Missing .env.prod — run: cp .env.prod.example .env.prod" && exit 1

dev: .env.dev ## Build and run the development stack in the foreground
	$(DEV_COMPOSE) up --build

dev-down: .env.dev ## Stop the development stack (keeps volumes)
	$(DEV_COMPOSE) down

dev-logs: .env.dev ## Follow development stack logs
	$(DEV_COMPOSE) logs -f

prod: .env.prod ## Build and start the production stack in the background
	$(PROD_COMPOSE) up -d --build

prod-down: .env.prod ## Stop the production stack (keeps volumes)
	$(PROD_COMPOSE) down

prod-logs: .env.prod ## Follow production stack logs
	$(PROD_COMPOSE) logs -f
