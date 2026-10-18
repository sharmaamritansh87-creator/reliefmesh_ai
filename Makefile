.PHONY: install run test web
install:
	pip install -r requirements.txt && cd frontend && npm i
run:
	python -m backend.run_all
web:
	cd frontend && npm run dev
test:
	python -m pytest -q
