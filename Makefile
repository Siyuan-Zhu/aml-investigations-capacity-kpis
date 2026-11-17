PY ?= python3
export PYTHONPATH := .

.PHONY: all simulate load forecast capacity figures report test clean

all: simulate load forecast capacity figures report

simulate:
	$(PY) -m src.simulate

load:
	$(PY) -m src.models

forecast:
	$(PY) -m src.forecast

capacity:
	$(PY) -m src.capacity

figures:
	$(PY) -m src.figures

report:
	$(PY) -m src.report

test:
	$(PY) -m pytest -q

clean:
	rm -rf data outputs
