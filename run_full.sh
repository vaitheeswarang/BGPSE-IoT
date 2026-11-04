#!/usr/bin/env bash
set -e
python -m scripts.run_performance_study --config configs/full.json --outdir results/performance
