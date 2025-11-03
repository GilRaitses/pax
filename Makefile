FIGURE_DIR := outputs/figures

.PHONY: figure4 warehouse

figure4:
	python -m pax.scripts.render_routes --output-dir $(FIGURE_DIR)

warehouse:
	python -m pax.scripts.warehouse

