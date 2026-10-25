# Resource admission review lab

Portable offline source and tests for development admission, resource observations, disposable SQLite reservation/recovery and separate signed witness review.

boundary_review.py adds bounded Python source-syntax observation without importing or executing worker source. Function names, literal request sets and call syntax are observations only; comments, metadata and a named admission function never establish trusted admission, current ownership, liveness or K003 compatibility.

d7_compatibility.py reviews the historical three-field broker request, not the larger Rust IPC payload. It reuses the existing DEV result observer and resource/identity review, then checks the unchanged pinned K003 job schema. A DEV build is not silently converted to executable runtime. Missing mapping/authority stays HOLD; status remains query-only and no query is performed. Unsigned development results never require production signing credentials, and a prebuild review does not require a prior build result.

Install the pinned review dependencies from requirements.txt, then run:

```text
python -B run_review.py --verify-only
python -B run_review.py --out ../review-evidence
```

The output directory must be new and outside this source package. The entry point checks source byte pins, selects its own pytest configuration/root and excludes parent conftest files. It verifies that every review module/fixture was imported from this package. The M011 test file is retained as an unchanged fixture dependency; the entry point selects the reviewed suites explicitly.

There is one current disposable resource authority implementation. authority.py only exposes compatibility contract names from that implementation; it does not add another scheduler or admission service. Existing source ancestry is recorded in MANIFEST.json. Keep these raw bytes unchanged across newline conversion because verifier source identity is pinned.

This package creates only synthetic temporary test state and ephemeral fixture keys. It provides no live telemetry, independent provider, worker dispatch, production signing, publishing or database migration. Passing source/tests is not production acceptance. Do not install the lab on an active worker or treat its marker, callback or fixture signature as authority.
