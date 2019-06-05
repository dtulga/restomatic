.PHONY: clean requirements local package release test coverage

clean:
	rm -rf dist/*

requirements:
	pip3 install -r test-requirements.txt

local:
	pip3 install -e .

package:
	python3 setup.py sdist bdist_wheel

release: clean package
	twine upload dist/*

test:
	pytest tests

coverage:
	pytest tests --cov=restomatic --cov-report html:htmlcov
