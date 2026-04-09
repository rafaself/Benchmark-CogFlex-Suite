.PHONY: notelab test build-private verify-public verify-private deploy-dataset deploy-private-dataset deploy-notebook deploy-all

notelab:
	.venv/bin/jupyter lab --no-browser kaggle/notebook/cogflex_notebook_task.ipynb

test:
	.venv/bin/python -m unittest discover -s tests -q

build-private:
	.venv/bin/python -m scripts.build_private_cogflex_dataset

verify-public:
	.venv/bin/python -m scripts.verify_cogflex --split public

verify-private:
	.venv/bin/python -m scripts.verify_cogflex --split private

deploy-dataset:
	./scripts/deploy_dataset.sh

deploy-private-dataset:
	./scripts/deploy_private_dataset.sh

deploy-notebook:
	./scripts/deploy_notebook.sh

deploy-all: deploy-dataset deploy-private-dataset deploy-notebook
