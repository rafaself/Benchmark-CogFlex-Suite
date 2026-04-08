.PHONY: notelab test verify-public verify-private deploy-dataset deploy-private-dataset deploy-notebook deploy-all

notelab:
	.venv/bin/jupyter lab --no-browser kaggle/notebook/ruleshift_notebook_task.ipynb

test:
	.venv/bin/python -m unittest discover -s tests -q

verify-public:
	.venv/bin/python -m scripts.verify_ruleshift --split public

verify-private:
	.venv/bin/python -m scripts.verify_ruleshift --split private

deploy-dataset:
	./scripts/deploy_dataset.sh

deploy-private-dataset:
	./scripts/deploy_private_dataset.sh

deploy-notebook:
	./scripts/deploy_notebook.sh

deploy-all: deploy-dataset deploy-private-dataset deploy-notebook
