#bin/bash
#Runs type checking and all tests on the project
mypy main.py
mypy src/analyse_conf/*.py
mypy tests/*.py
pytest -v tests/*.py
