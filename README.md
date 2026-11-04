# BGPSE-IoT Expanded Baselines, Ablation, and Stage-Wise Timing Package

### Stage-wise profiling
Encryption profiling includes ECDH, HKDF, content digest, GFSR seed hierarchy, dynamic S-box construction, permutation, mask generation, substitution, forward diffusion, reverse diffusion, AES-GCM, HMAC, ECDSA, and total encryption time.

## Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Windows activation: `.venv\\Scripts\\activate`

## Verify environment
```bash
python -m scripts.check_environment
pytest -q
```

## Quick smoke test
```bash
python -m scripts.generate_demo_dataset --root datasets/demo --n 3
python -m scripts.run_performance_study --config configs/quick.json --outdir results/quick
```

## Full benchmark
Copy or link the already prepared five-dataset corpus into:
```text
datasets/processed/
  kodak/
  usc_sipi/
  bsds500/
  div2k/
  medmnist/
```
Any nested image files are accepted.

Run:
```bash
python -m scripts.run_performance_study --config configs/full.json --outdir results/performance
```

## Single-image deep stage profile
```bash
python -m scripts.run_stage_profile datasets/processed/kodak/<image>.png --size 512 --repetitions 30 --out results/stage_profile_single.csv
```

## Key outputs
- `baseline_timing_results.csv`: per-image direct comparison
- `timing_summary.csv`: method/resolution aggregate
- `timing_statistical_tests.csv`: Friedman + paired Wilcoxon + Holm correction
- `bgpse_stage_timing_results.csv`: raw stage measurements
- `bgpse_stage_timing_summary.csv`: encryption-stage medians, P95, contribution percentages
- `bgpse_decrypt_stage_timing_summary.csv`: decryption-stage medians, P95, contribution percentages
- `bgpse_ablation_timing_results.csv`: per-image ablations
- `bgpse_ablation_summary.csv`: ablation summary and percent change from full method
- `figures/`: 400-dpi publication plots
