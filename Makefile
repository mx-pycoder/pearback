SHELL := /bin/bash

.PHONY: help
help:
	@echo
	@echo "makefile targets"
	@echo "----------------"
	@echo "  make wheel       - create python3 wheel"
	@echo "  make clean       - remove build data and compiled files"
	@echo "  make clean-dist  - return to checkout state"
	@echo "  make install     - install via pip3 (need sudo)"
	@echo "  make uninstall   - uninstall via pip3 (need sudo)"
	@echo ""

.PHONY: wheel
wheel:
	python3 setup.py bdist_wheel

.PHONY: clean
clean:
	rm -rf pearback.egg-info
	rm -rf build
	rm -rf pearback/__pycache__
	rm -rf pearback/*.pyc
	rm -rf __pycache__

.PHONY: clean-dist
clean-dist: clean
	rm -rf dist

.PHONY: install
install:
	pip3 install .

.PHONY: uninstall
uninstall:
	pip3 uninstall pearback


