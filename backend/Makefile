install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

seed:
	python scripts/seed_demo_data.py

demo:
	python scripts/run_demo_cases.py

test:
	pytest -q

smoke:
	python scripts/smoke_test.py
