"""
compress_models.py
Re-saves your model files with compression so they fit GitHub's 25 MB
web-upload limit. The models are identical; joblib.load() reads
compressed files automatically, so no other code changes.

IMPORTANT: run this on YOUR computer (same environment you trained in),
so the files keep scikit-learn's original version tag.

Usage (put next to your original .joblib files):
    python compress_models.py
"""
import os
import joblib

for name in ('fraud_rf.joblib', 'isolation_forest.joblib'):
    before = os.path.getsize(name) / 1e6
    model = joblib.load(name)
    out = name.replace('.joblib', '_small.joblib')
    joblib.dump(model, out, compress=3)
    after = os.path.getsize(out) / 1e6
    print(f'{name}: {before:.1f} MB -> {out}: {after:.1f} MB')

print('\nRename the *_small.joblib files back to the original names before uploading.')
