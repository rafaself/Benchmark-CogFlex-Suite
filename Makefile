PYTHON ?= python3

.PHONY: deploy

deploy:
	$(PYTHON) -m scripts.deploy $(ARGS)
