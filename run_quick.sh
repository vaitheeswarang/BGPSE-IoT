#!/usr/bin/env bash
set -e
python -m scripts.generate_demo_dataset --root datasets/demo --n 3
python -m scripts.run_performance_study --config configs/quick.json --outdir results/quick
