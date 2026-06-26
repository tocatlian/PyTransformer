PYTHON ?= python3
PYTHONPATH := src
COMMAND_MODULES := \
	pyt_files_append_folder_name \
	pyt_help \
	pyt_jpeg_show_metadata \
	pyt_jpeg_strip_metadata \
	pyt_jpeg_count_variants \
	pyt_mp4_split_chunks \
	pyt_mp4_transcribe_batch \
	pyt_mp4_transcribe \
	pyt_pdf_extract_selectable_text_batch \
	pyt_pdf_extract_selectable_text \
	pyt_pdf_render_jpeg \
	pyt_pdf_extract_text \
	pyt_text_concatenate
CONSOLE_COMMANDS := \
	pyt-files-append-folder-name \
	pyt-help \
	pyt-jpeg-show-metadata \
	pyt-jpeg-strip-metadata \
	pyt-jpeg-count-variants \
	pyt-mp4-split-chunks \
	pyt-mp4-transcribe-batch \
	pyt-mp4-transcribe \
	pyt-pdf-extract-selectable-text-batch \
	pyt-pdf-extract-selectable-text \
	pyt-pdf-render-jpeg \
	pyt-pdf-extract-text \
	pyt-text-concatenate

.PHONY: help validate compile lint format-check type-check coverage hook-config-check hooks help-check entrypoint-check test build-check smoke clean

help:
	@printf '%s\n' 'Available targets:'
	@printf '%s\n' '  make validate    Run compile, lint, format, help, entrypoint, test, and build checks.'
	@printf '%s\n' '  make compile     Compile package and tests.'
	@printf '%s\n' '  make lint        Run Ruff lint checks.'
	@printf '%s\n' '  make format-check Check Ruff formatting.'
	@printf '%s\n' '  make type-check  Run mypy static type checks.'
	@printf '%s\n' '  make coverage    Run tests with coverage reporting.'
	@printf '%s\n' '  make hook-config-check Validate pre-commit hook configuration.'
	@printf '%s\n' '  make hooks       Run pre-commit hooks across the repository.'
	@printf '%s\n' '  make help-check  Verify every command module exposes --help.'
	@printf '%s\n' '  make entrypoint-check Verify installed console commands expose --help.'
	@printf '%s\n' '  make test        Run the standard-library unittest suite.'
	@printf '%s\n' '  make build-check Build sdist/wheel in a temp folder and verify metadata.'
	@printf '%s\n' '  make smoke       Run representative standard-library commands on temp fixtures.'
	@printf '%s\n' '  make clean       Remove local Python/cache/build artifacts.'

validate: compile lint format-check type-check hook-config-check help-check entrypoint-check test coverage build-check

compile:
	$(PYTHON) -m compileall -q src tests

lint:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m ruff check src tests

format-check:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m ruff format --check src tests

type-check:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m mypy

hook-config-check:
	$(PYTHON) -m pre_commit validate-config

hooks:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pre_commit run --all-files

help-check:
	@set -eu; \
	for module in $(COMMAND_MODULES); do \
		printf 'checking pytransformer.cli.%s --help\n' "$$module"; \
		PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m "pytransformer.cli.$$module" --help >/dev/null; \
	done

entrypoint-check:
	@set -eu; \
	python_bin="$$(dirname "$$($(PYTHON) -c 'import sys; print(sys.executable)')")"; \
	for command_name in $(CONSOLE_COMMANDS); do \
		command_path=""; \
		if [ -x "$$python_bin/$$command_name" ]; then \
			command_path="$$python_bin/$$command_name"; \
		else \
			command_path="$$(command -v "$$command_name" || true)"; \
		fi; \
		if [ -z "$$command_path" ]; then \
			printf 'missing installed command: %s\n' "$$command_name" >&2; \
			exit 1; \
		fi; \
		printf 'checking %s --help\n' "$$command_name"; \
		"$$command_path" --help >/dev/null; \
	done

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

coverage:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m coverage run -m unittest discover -s tests -v
	$(PYTHON) -m coverage report

build-check:
	@tmpdir="$$(mktemp -d)"; \
	build_log="$$(mktemp)"; \
	trap 'rm -f "$$build_log"; rm -rf "$$tmpdir" build src/*.egg-info *.egg-info' EXIT; \
	if ! $(PYTHON) -m build --sdist --wheel --outdir "$$tmpdir" > "$$build_log" 2>&1; then \
		cat "$$build_log"; \
		exit 1; \
	fi; \
	$(PYTHON) -m twine check "$$tmpdir"/*.tar.gz "$$tmpdir"/*.whl

smoke:
	@tmpdir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	mkdir -p "$$tmpdir/texts" "$$tmpdir/images" "$$tmpdir/rename/Tokyo"; \
	printf 'alpha\n' > "$$tmpdir/texts/a.txt"; \
	printf 'beta\n' > "$$tmpdir/texts/b.txt"; \
	touch "$$tmpdir/images/photo-warm.jpg" "$$tmpdir/images/photo-cool.jpg" "$$tmpdir/images/skip.png"; \
	printf 'one' > "$$tmpdir/rename/Tokyo/one.jpg"; \
	printf 'two' > "$$tmpdir/rename/Tokyo/two.txt"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_text_concatenate --output "$$tmpdir/combined.txt" "$$tmpdir/texts"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_help --names-only; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_jpeg_count_variants --list-presets "$$tmpdir/images"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_files_append_folder_name --dry-run "$$tmpdir/rename/Tokyo"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_files_append_folder_name --yes "$$tmpdir/rename/Tokyo"

clean:
	rm -rf __pycache__ tests/__pycache__ src/pytransformer/__pycache__ src/pytransformer/cli/__pycache__ src/pytransformer/core/__pycache__
	rm -rf .coverage coverage.xml .pytest_cache .mypy_cache .ruff_cache build dist htmlcov pip-wheel-metadata *.egg-info src/*.egg-info
	find . -name '*.pyc' -delete
