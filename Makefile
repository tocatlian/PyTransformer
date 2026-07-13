PYTHON ?= python3
PYTHONPATH := src
COMMAND_MODULES := \
	pyt_files_append_folder_name \
	pyt_image_split \
	pyt_image_to_webp \
	pyt_help \
	pyt_jpeg_show_metadata \
	pyt_jpeg_strip_metadata \
	pyt_image_variants_count \
	pyt_image_collage_slice \
	pyt_m4a_to_mp3 \
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
	pyt-image-split \
	pyt-image-to-webp \
	pyt-help \
	pyt-jpeg-show-metadata \
	pyt-jpeg-strip-metadata \
	pyt-image-variants-count \
	pyt-image-collage-slice \
	pyt-m4a-to-mp3 \
	pyt-mp4-split-chunks \
	pyt-mp4-transcribe-batch \
	pyt-mp4-transcribe \
	pyt-pdf-extract-selectable-text-batch \
	pyt-pdf-extract-selectable-text \
	pyt-pdf-render-jpeg \
	pyt-pdf-extract-text \
	pyt-text-concatenate

.PHONY: help validate validate-all compile lint format-check type-check coverage hook-config-check hooks help-check entrypoint-check docs docs-check docs-watch test build-check tox smoke smoke-optional smoke-pdf smoke-jpeg smoke-m4a clean

help:
	@printf '%s\n' 'Available targets:'
	@printf '%s\n' '  make validate    Run compile, lint, format, docs, help, entrypoint, test, and build checks.'
	@printf '%s\n' '  make validate-all Run validate plus optional dependency smoke checks.'
	@printf '%s\n' '  make compile     Compile package and tests.'
	@printf '%s\n' '  make lint        Run Ruff lint checks.'
	@printf '%s\n' '  make format-check Check Ruff formatting.'
	@printf '%s\n' '  make type-check  Run mypy static type checks.'
	@printf '%s\n' '  make coverage    Run tests with coverage reporting.'
	@printf '%s\n' '  make hook-config-check Validate pre-commit hook configuration.'
	@printf '%s\n' '  make hooks       Run pre-commit hooks across the repository.'
	@printf '%s\n' '  make help-check  Verify every command module exposes --help.'
	@printf '%s\n' '  make entrypoint-check Verify installed console commands expose --help.'
	@printf '%s\n' '  make docs        Build static HTML documentation from markdown.'
	@printf '%s\n' '  make docs-check  Verify generated HTML documentation is current.'
	@printf '%s\n' '  make docs-watch  Rebuild HTML documentation when markdown changes.'
	@printf '%s\n' '  make test        Run the standard-library unittest suite.'
	@printf '%s\n' '  make build-check Build sdist/wheel in a temp folder and verify metadata.'
	@printf '%s\n' '  make tox         Run the configured tox environments.'
	@printf '%s\n' '  make smoke       Run representative standard-library commands on temp fixtures.'
	@printf '%s\n' '  make smoke-optional Run optional PDF, JPEG, and M4A smoke checks.'
	@printf '%s\n' '  make smoke-pdf   Run PDF commands against a generated fixture; requires .[pdf].'
	@printf '%s\n' '  make smoke-jpeg  Run JPEG commands against generated fixtures; requires .[jpeg].'
	@printf '%s\n' '  make smoke-m4a   Run M4A-to-MP3 commands against generated fixtures; requires FFmpeg.'
	@printf '%s\n' '  make clean       Remove local Python/cache/build artifacts.'

validate: compile lint format-check type-check hook-config-check docs-check help-check entrypoint-check test coverage build-check

validate-all: validate smoke-optional

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

docs:
	$(PYTHON) scripts/build_docs.py

docs-check:
	$(PYTHON) scripts/build_docs.py --check

docs-watch:
	$(PYTHON) scripts/build_docs.py --watch

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

tox:
	$(PYTHON) -m tox

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
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_image_variants_count --list-presets "$$tmpdir/images"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_files_append_folder_name --dry-run "$$tmpdir/rename/Tokyo"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_files_append_folder_name --yes "$$tmpdir/rename/Tokyo"

smoke-optional: smoke-pdf smoke-jpeg smoke-m4a

smoke-m4a:
	@tmpdir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	mkdir -p "$$tmpdir/audio"; \
	ffmpeg -hide_banner -loglevel error -y -f lavfi -i sine=frequency=1000:duration=0.2 -c:a aac "$$tmpdir/audio/first.m4a"; \
	ffmpeg -hide_banner -loglevel error -y -f lavfi -i sine=frequency=1200:duration=0.2 -c:a aac "$$tmpdir/audio/second.m4a"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_m4a_to_mp3 --bitrate 192k "$$tmpdir/audio/first.m4a" "$$tmpdir/audio/second.m4a"; \
	test -s "$$tmpdir/audio/first.mp3"; \
	test -s "$$tmpdir/audio/second.mp3"

smoke-pdf:
	@tmpdir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	mkdir -p "$$tmpdir/pdfs" "$$tmpdir/batch-text" "$$tmpdir/rendered"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -c 'import sys; from pathlib import Path; import fitz; pdf_path = Path(sys.argv[1]); doc = fitz.open(); page = doc.new_page(); page.insert_text((72, 72), "PyTransformer PDF smoke fixture"); doc.save(pdf_path); doc.close()' "$$tmpdir/pdfs/sample.pdf"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_pdf_extract_selectable_text --output "$$tmpdir/selectable.txt" "$$tmpdir/pdfs/sample.pdf"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_pdf_extract_selectable_text_batch --output-folder "$$tmpdir/batch-text" "$$tmpdir/pdfs"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_pdf_extract_text --no-ocr --output "$$tmpdir/extracted.txt" "$$tmpdir/pdfs/sample.pdf"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_pdf_render_jpeg --dpi 72 --quality 75 --output-folder "$$tmpdir/rendered" "$$tmpdir/pdfs/sample.pdf"; \
	test -s "$$tmpdir/selectable.txt"; \
	test -s "$$tmpdir/batch-text/sample.txt"; \
	test -s "$$tmpdir/extracted.txt"; \
	test -f "$$tmpdir/rendered/page_1.jpg"

smoke-jpeg:
	@tmpdir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	mkdir -p "$$tmpdir/images" "$$tmpdir/clean"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -c 'import sys; from pathlib import Path; from PIL import Image; folder = Path(sys.argv[1]); exif = Image.Exif(); exif[0x010F] = "PyTransformer"; exif[0x0131] = "Smoke"; colors = {"photo-warm.jpg": (220, 120, 90), "photo-cool.jpg": (70, 130, 210), "photo-neutral.jpg": (140, 140, 140)}; [Image.new("RGB", (24, 24), color).save(folder / name, "JPEG", exif=exif, comment=b"private smoke comment") for name, color in colors.items()]' "$$tmpdir/images"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_jpeg_show_metadata "$$tmpdir/images/photo-warm.jpg"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_image_to_webp --quality 98 "$$tmpdir/images/photo-warm.jpg" "$$tmpdir/images/photo-cool.jpg"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_image_variants_count --list-presets "$$tmpdir/images"; \
	cd "$$tmpdir" && PYTHONPATH="$(CURDIR)/$(PYTHONPATH)" $(PYTHON) -m pytransformer.cli.pyt_image_collage_slice 8 "$$tmpdir/images/photo-warm.jpg" "$$tmpdir/images/photo-cool.jpg" "$$tmpdir/images/photo-neutral.jpg"; \
	cd "$$tmpdir" && PYTHONPATH="$(CURDIR)/$(PYTHONPATH)" $(PYTHON) -m pytransformer.cli.pyt_image_collage_slice --tiff --output "$$tmpdir/collage.tif" 8 "$$tmpdir/images/photo-warm.jpg" "$$tmpdir/images/photo-cool.jpg" "$$tmpdir/images/photo-neutral.jpg"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_jpeg_strip_metadata --quiet --output-folder "$$tmpdir/clean" "$$tmpdir/images"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytransformer.cli.pyt_jpeg_show_metadata "$$tmpdir/clean/photo-warm.jpg"; \
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -c 'import sys; from pathlib import Path; from pytransformer.core.jpeg_metadata import inspect_embedded_metadata; metadata = inspect_embedded_metadata(Path(sys.argv[1])); leftovers = sorted(key for key in metadata if key.startswith("EXIF.") or key == "INFO.comment"); sys.exit(f"metadata was not stripped: {leftovers}") if leftovers else None' "$$tmpdir/clean/photo-warm.jpg"; \
	test -f "$$tmpdir/clean/photo-warm.jpg"; \
	test -f "$$tmpdir/clean/photo-cool.jpg"; \
	test -f "$$tmpdir/images/photo-warm.webp"; \
	test -f "$$tmpdir/images/photo-cool.webp"; \
	test -f "$$tmpdir/photo-warm+photo-cool+photo-neutral-8px-strips.jpg"; \
	test -f "$$tmpdir/collage.tif"

clean:
	rm -rf __pycache__ tests/__pycache__ src/pytransformer/__pycache__ src/pytransformer/cli/__pycache__ src/pytransformer/core/__pycache__
	rm -rf .coverage coverage.xml .pytest_cache .mypy_cache .ruff_cache .tox build dist htmlcov pip-wheel-metadata *.egg-info src/*.egg-info
	find . -name '*.pyc' -delete
