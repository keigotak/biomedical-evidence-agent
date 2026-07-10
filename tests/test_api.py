from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from biomedical_evidence_agent import paths

# The path-resolution tests are stdlib-only and must run everywhere (they guard
# the Docker bug). The run_audit test needs the ``[api]`` extra (pydantic); skip
# it cleanly when only the dependency-free core is installed, e.g. the CI job
# that runs ``pip install -e .`` — keeping the core-only test run green.
try:
    from biomedical_evidence_agent.api import (
        AuditRequest,
        CORPUS_PATH,
        WEB_DIST,
        run_audit,
    )

    _API_AVAILABLE = True
except ImportError:
    _API_AVAILABLE = False
    CORPUS_PATH = paths.data_path("sample_corpus.jsonl")
    WEB_DIST = paths.app_root() / "web" / "dist"


class DataPathResolutionTest(unittest.TestCase):
    """The data/ dir must resolve independently of where the package is installed.

    Regression guard for the Docker bug where a non-editable ``pip install``
    moved the modules into site-packages and the old ``__file__.parents[2]``
    resolution pointed the corpus/ontology paths into the Python install tree.
    """

    def tearDown(self) -> None:
        os.environ.pop("BIOCLAIM_ROOT", None)
        paths.data_dir.cache_clear()

    def test_default_data_dir_holds_the_bundled_corpus_and_ontology(self) -> None:
        paths.data_dir.cache_clear()
        data_dir = paths.data_dir()
        self.assertTrue((data_dir / "ontology.jsonl").is_file())
        self.assertTrue((data_dir / "sample_corpus.jsonl").is_file())

    def test_api_module_paths_point_at_real_files(self) -> None:
        self.assertTrue(CORPUS_PATH.is_file())
        # web/dist only exists after a frontend build; when present it must be a dir.
        self.assertTrue(WEB_DIST.name == "dist" and WEB_DIST.parent.name == "web")

    def test_env_override_wins_over_module_location(self) -> None:
        with TemporaryDirectory() as tmp:
            fake_data = Path(tmp) / "data"
            fake_data.mkdir()
            (fake_data / "ontology.jsonl").write_text("{}\n", encoding="utf-8")
            os.environ["BIOCLAIM_ROOT"] = tmp
            paths.data_dir.cache_clear()
            self.assertEqual(paths.data_dir(), fake_data)


@unittest.skipUnless(_API_AVAILABLE, "requires the [api] extra (pydantic)")
class RunAuditTest(unittest.TestCase):
    """End-to-end exercise of the API's pipeline wrapper (framework-free).

    Covers the whole audit path the FastAPI route runs — retrieval, evidence
    card, deterministic audit, mock review, rendered payload — offline.
    """

    def test_contested_claim_produces_a_gradeable_payload(self) -> None:
        req = AuditRequest(
            claim="BRAF V600E melanoma is associated with response to targeted inhibitor treatment.",
            source="sample",
            retriever="concept",
            top_k=3,
            reviewer="mock",
        )
        payload = run_audit(req)
        self.assertEqual(payload["verdict"]["label"], "contested")
        self.assertEqual(payload["records_retrieved"], 3)
        self.assertTrue(payload["markdown"])
        self.assertIn("settings", payload)
        # The resolution path exposes at least one grounded next step.
        self.assertTrue(payload["resolution_path"])


if __name__ == "__main__":
    unittest.main()
