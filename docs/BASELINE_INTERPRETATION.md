# Baseline interpretation rules

## Direct standardized baselines
The following are direct executable baselines under the same Python process and image bytes:
- AES-256-GCM
- ChaCha20-Poly1305
- AES-CTR + HMAC-SHA-256
- AES-CBC + HMAC-SHA-256
- ECIES-style P-256 ECDH + HKDF + AES-GCM

These can be compared directly for runtime on the same machine, while noting that Python/library implementations differ internally.

## Literature-family reference implementations
- CA-ECC-Reference
- ECC-DynamicSBox-Reference

These reproduce broad technique families only. They are **not exact implementations of EHIES-ECCCA, Murtaza-Hayat, or any other named published paper** unless author code/specifications are independently matched line by line. Do not label their numerical values as those papers' results.

Recommended manuscript wording: "Two technique-family reference implementations were added under a common software environment to contextualize the costs of cellular-automata/ECC and ECC/dynamic-S-box processing; these are not claimed as exact reproductions of published source code."
