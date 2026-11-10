"""
fraud_scoring.py
Shared scoring logic used by both the Kafka streaming detector
and the on-demand transaction-lookup API. Keeping this in one
place means the "live stream" view and the "look up one ID" view
can never silently disagree with each other.
"""

import os
import joblib

RF_MODEL_PATH  = 'fraud_rf.joblib'
ISO_MODEL_PATH = 'isolation_forest.joblib'
FRAUD_PROB_THRESHOLD = 0.5

TYPE_MAP = {'CASH_IN': 0, 'CASH_OUT': 1, 'DEBIT': 2, 'PAYMENT': 3, 'TRANSFER': 4}


def load_models():
    """Load both models once. Call this at process startup, not per-request."""
    models = {'rf': None, 'iso': None}
    if os.path.exists(RF_MODEL_PATH):
        models['rf'] = joblib.load(RF_MODEL_PATH)
    if os.path.exists(ISO_MODEL_PATH):
        models['iso'] = joblib.load(ISO_MODEL_PATH)
    return models


def rf_features(tx):
    a, oo, no, od, nd, t = (tx['amount'], tx['oldbalanceOrg'], tx['newbalanceOrig'],
                             tx['oldbalanceDest'], tx['newbalanceDest'], tx['type'])
    return [[a, oo, no, od, nd,
             TYPE_MAP.get(t, -1),
             1 if t in ('TRANSFER', 'CASH_OUT') else 0,
             1 if (no == 0 and oo > 0) else 0]]


def iso_features(tx):
    return [[tx['amount'], tx['oldbalanceOrg'], tx['newbalanceOrig'],
             tx['oldbalanceDest'], tx['newbalanceDest']]]


def rule_flag(tx):
    return (
        tx['type'] in ('TRANSFER', 'CASH_OUT') and
        tx['newbalanceOrig'] == 0 and
        tx['oldbalanceOrg'] > 0 and
        tx['amount'] > 100_000
    )


def rf_flag(tx, models):
    if models.get('rf') is None:
        return False, 0.0
    prob = float(models['rf'].predict_proba(rf_features(tx))[0][1])
    return prob >= FRAUD_PROB_THRESHOLD, prob


def iso_flag(tx, models):
    if models.get('iso') is None:
        return False
    result = models['iso'].predict(iso_features(tx))[0]
    return bool(result == -1)  # -1 = anomaly


def score_transaction(tx, models):
    """
    Runs all three layers on a single transaction dict and returns
    a structured verdict. `tx` must contain: type, amount, oldbalanceOrg,
    newbalanceOrig, oldbalanceDest, newbalanceDest (isFraud optional,
    used only for display when ground truth is known).
    """
    rule_hit        = rule_flag(tx)
    rf_hit, rf_prob = rf_flag(tx, models)
    iso_hit         = iso_flag(tx, models)

    layers = []
    if rule_hit: layers.append('RULE')
    if rf_hit:   layers.append('RF')
    if iso_hit:  layers.append('ISO')

    is_flagged = bool(layers)

    # Simple blended confidence: rule/iso are binary signals, RF gives a
    # probability. If nothing else, fall back to the RF probability alone.
    if is_flagged:
        confidence = max(rf_prob, 0.9 if rule_hit else 0.0, 0.75 if iso_hit else 0.0)
    else:
        confidence = rf_prob

    return {
        'transaction_id': tx.get('transaction_id'),
        'is_flagged': is_flagged,
        'confidence': round(confidence, 4),
        'layers_triggered': layers,
        'layer_detail': {
            'rule_engine': rule_hit,
            'random_forest': {'flagged': rf_hit, 'probability': round(rf_prob, 4)},
            'isolation_forest': {'flagged': iso_hit},
        },
        'actual_label': tx.get('isFraud'),  # only present if ground truth known
    }
