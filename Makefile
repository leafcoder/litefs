PYTHON=`which python`

install:
	$(PYTHON) setup.py install

# 构建源码包
build: wheel
	$(PYTHON) setup.py build sdist

build_ext:
	$(PYTHON) setup.py build_ext --inplace

# 构建 wheel 包
wheel:
	$(PYTHON) setup.py bdist_wheel

upload-test:
	pip install twine; \
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

upload:
	pip install twine; \
	twine upload dist/*

clean:
	rm -rf build dist *.egg-info __pycache__ tests/__pycache__ tests/*.pyc

.PHONY: test upload upload-test build wheel install clean
