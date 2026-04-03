.PHONY: notelab deploy-dataset deploy-private-dataset deploy-notebook deploy-all

notelab:
	.venv/bin/jupyter lab --no-browser kaggle/notebook/ruleshift_notebook_task.ipynb

deploy-dataset:
	./scripts/deploy_dataset.sh

deploy-private-dataset:
	./scripts/deploy_private_dataset.sh

deploy-notebook:
	./scripts/deploy_notebook.sh

deploy-all: deploy-dataset deploy-private-dataset deploy-notebook
