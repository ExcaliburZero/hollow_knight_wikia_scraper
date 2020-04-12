.PHONY: typecheck check-formatting format unit-test test

test:
	$(MAKE) format
	$(MAKE) typecheck
	$(MAKE) unit-test

typecheck:
	mypy hollow_knight_wikia_scraper/*.py --ignore-missing-imports --strict --html-report type-checking

check-formatting:
	black **/*.py --check

format:
	black **/*.py

unit-test:
	python -m nose