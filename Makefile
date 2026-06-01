run:
	streamlit run src/app.py

test:
	python -m pytest tests/ -v

lint:
	flake8 src/ tests/

install:
	pip install -r requirements.txt