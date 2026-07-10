"""Locate the bundled ``data/`` directory across install layouts.

The corpus, ontology and evaluation gold all live in the repo's ``data/``
directory. Resolving them off ``__file__`` (the old ``parents[2]`` pattern) works
from a source checkout but breaks the moment the package is pip-installed
non-editably — the load-bearing case being the Docker image, where this module
ends up in ``site-packages`` while the data is copied under the ``/app`` working
directory, so ``parents[2]`` points into the Python install tree instead.

So we search a list of candidate roots for a marker file — the ``BIOCLAIM_ROOT``
override first, then the working directory (``/app`` in Docker), then this
module's ancestors (the editable checkout) — and cache the winner.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# ``ontology.jsonl`` is always present in ``data/`` and is small — a reliable
# marker for "this directory is the app root".
_MARKER = Path("data") / "ontology.jsonl"


@lru_cache(maxsize=1)
def data_dir() -> Path:
    """Return the absolute path to the bundled ``data/`` directory."""

    module_file = Path(__file__).resolve()
    candidates: list[Path] = []
    env_root = os.environ.get("BIOCLAIM_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    cwd = Path.cwd().resolve()
    candidates.extend([cwd, *cwd.parents])
    candidates.extend(module_file.parents)
    for root in candidates:
        if (root / _MARKER).is_file():
            return root / "data"
    # Historical fallback: two levels up from this module (source checkout).
    root = module_file.parents[2] if len(module_file.parents) > 2 else cwd
    return root / "data"


def app_root() -> Path:
    """Return the directory that contains ``data/`` (and, in prod, ``web/dist``)."""

    return data_dir().parent


def data_path(name: str) -> Path:
    """Return the path to ``data/<name>``."""

    return data_dir() / name
