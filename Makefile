.PHONY: install test lint check update app

install:
	python -m pip install -e ".[dev,models]"

test:
	pytest

lint:
	ruff check .

check:
	python scripts/check_text_rules.py

update:
	python scripts/update_market_data.py

app:
	streamlit run app/app.py
