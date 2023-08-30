#bin/zsh
#Runs type checking and all tests on the project
alias python='/usr/local/bin/python3'
python -m mypy main.py
python -m mypy src/analyse_conf/*.py
python -m mypy tests/*.py
python -m pytest -v tests/*.py
