"""Exact set-difference metrics derived from elements, never submitted counts."""
from __future__ import annotations

from typing import Dict, Iterable, Set


def set_confusion(predicted: Iterable[str], gold: Iterable[str]) -> Dict[str, object]:
    pred: Set[str] = set(predicted)
    truth: Set[str] = set(gold)
    tp = pred & truth
    fp = pred - truth
    fn = truth - pred
    return {
        "tp": len(tp), "fp": len(fp), "fn": len(fn),
        "tp_items": sorted(tp), "fp_items": sorted(fp), "fn_items": sorted(fn),
        "exact": pred == truth,
    }
