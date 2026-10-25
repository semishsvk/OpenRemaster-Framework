# Resource admission review lab

Portable offline source and tests for development admission, resource observations, disposable SQLite reservation/recovery and separate signed witness review.

Install the pinned review dependencies from requirements.txt, then run:

```text
python -B run_review.py --verify-only
python -B run_review.py --out ../review-evidence
```

The output directory must be new and outside this source package. The entry point checks source byte pins and verifies that every review module/fixture was imported from this package. The M011 test file is retained as an unchanged fixture dependency; the entry point selects the reviewed suites explicitly.

There is one current disposable resource authority implementation. authority.py only exposes compatibility contract names from that implementation; it does not add another scheduler or admission service. Existing source ancestry is recorded in MANIFEST.json. Keep these raw bytes unchanged across newline conversion because verifier source identity is pinned.

This package creates only synthetic temporary test state and ephemeral fixture keys. It provides no live telemetry, independent provider, worker dispatch, production signing, publishing or database migration. Passing source/tests is not production acceptance. Do not install the lab on an active worker or treat its marker, callback or fixture signature as authority.
