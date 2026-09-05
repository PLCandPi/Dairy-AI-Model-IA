#!/data/data/com.termux/files/usr/bin/bash
# One-shot environment setup for Termux. Safe to re-run.
#
# torch comes from pkg, never pip: PyPI has no manylinux-compatible wheels for
# Termux's Bionic/Android target, so `pip install torch` always fails here.
# rust is needed because peft/transformers pull in tokenizers and safetensors,
# which are Rust extensions with no prebuilt Android wheel either - pip will
# compile them from source, and that needs a native (not rustup-bootstrapped)
# toolchain, since rustup doesn't ship an aarch64-linux-android target.
set -e

pkg update -y
pkg install -y python-torch rust python git

pip install -r "$(dirname "$0")/requirements.txt"

echo "Setup complete. Run: python train.py"
