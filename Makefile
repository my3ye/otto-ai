.PHONY: up down logs reset example shell

# Start all services (postgres, neo4j, graphiti, memory-api)
up:
	@cp -n .env.example .env 2>/dev/null || true
	docker compose up -d
	@echo ""
	@echo "Otto AI is starting. Check health with:"
	@echo "  curl http://localhost:8100/health"

# Stop all services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f memory-api

# Reset: stop, remove volumes, restart fresh
reset:
	docker compose down -v
	docker compose up -d

# Run the hello-memory example
example:
	@echo "Running hello-memory example..."
	cd examples/hello-memory && pip install -q requests && python agent.py

# Shell into the memory API container
shell:
	docker compose exec memory-api /bin/bash
