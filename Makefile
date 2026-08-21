PYTEST_TOOLS = --with 'pytest-cov>=6,<8' --with 'pytest-timeout>=2,<3' --with 'freezegun>=1,<2'
PYTEST = uv run $(PYTEST_TOOLS) pytest

.PHONY: test-all test-unit test-security test-gen6 test-chaos test-standards

test-all:
	$(PYTEST) -m 'not manual and not live_provider' --mock-provider --timeout=30 -q

test-unit:
	$(PYTEST) -m 'not slow and not manual and not live_provider' --mock-provider --timeout=30 -q

test-security:
	$(PYTEST) tests/security/ --mock-provider --attack-mode --timeout=30 -v

test-gen6:
	$(PYTEST) -m 'gen6_1 or gen6_2 or gen6_3' --mock-provider --timeout=30 --durations=10 -q

test-chaos:
	$(PYTEST) tests/chaos/ --mock-provider --chaos-level=3 --timeout=30 -v

test-standards:
	$(PYTEST) tests/test_chat_mcp_bridge.py tests/test_gen6_elastic_swarm.py tests/test_gen6_cognitive_memory.py \
		--mock-provider --timeout=30 \
		--cov=creator_app.core.chat_bridge \
		--cov=creator_app.core.mcp_bridge_manifest \
		--cov=creator_app.core.elastic_swarm_director \
		--cov=creator_app.core.memory_decay \
		--cov=creator_app.core.dream_consolidation \
		--cov=creator_app.core.experience_skill \
		--cov=creator_app.core.memory_regression \
		--cov-report=xml:coverage.xml --cov-fail-under=80 \
		--junitxml=junit.xml -q
