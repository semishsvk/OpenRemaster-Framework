# Source-only naming registry integration

`openremaster.naming` reuses the existing harmonization contract. It adds a read-only component reference consumer for the existing `ProjectManifest` class. No original Framework module or manifest schema was replaced.

Opt-in metadata keys are `orf_component_ref`, `orf_project_id` and optional `orf_edition_id`. Values are nonempty strings; the registry project scope is explicit and case-sensitive. Edition-specific references require an explicit edition. Canonical component IDs or admitted aliases such as K003 resolve through the supplied registry. The ordinary label is Execution Control.

`resolve_manifest_component(manifest, registry_path)` preserves the original manifest project ID. The selected registry project identifies the referenced component's scope, not a forced rename of the legacy game/project identity. Shared references may therefore target OpenRemaster while an existing manifest remains `openazrael`. This does not bind an actual corpus or confer ownership. Missing metadata returns None; invalid or unknown/conflicting references hold.

The example registry is a portable test fixture of the existing Naming Harmonization logical identities. Host paths, artifact locators, ownership and live source bindings are absent; the fixture is not an accepted project registry or installed production service. No implicit registry path, writer, dispatcher, signer or owner provider is introduced. All reference results keep owner_admission, rename_authorized and execution_authorized false.

CLI: `python -B -m openremaster.naming examples/naming/canonical-components.review.json --resolve K003`.

This source-only integration is stacked on the existing consolidation draft PR #27 at `d71716d72493bc170da9819df7081cc3b7ca5ba1`, not a replacement for accepted main or the newer Studio owner stream. Its existing local-preflight test/helper repair is retained unchanged. The existing missing-argparse CLI repair and two negative CLI guards are reused from the separately tested naming review.

The repository's existing Core and portable development acceptance profiles apply. A Windows symlink-privilege skip remains explicit; simulated tests do not replace the real check. Source-only test success does not grant GitHub writer, live owner, dispatch or release admission.

The portfolio and PKS project namespaces remain separate. No game source, corpus, edition, production worker or historical checkpoint is moved or rebound by these opt-in metadata references. The existing draft owner and remote refs remain unchanged until admitted review.

CLI scope validation: `--project` and `--edition` require an explicit `--resolve` selector. Empty or whitespace-only selectors and scopes return HOLD (exit 75). The standalone observed-location CLI likewise rejects project/edition filters on logical directory queries instead of returning unfiltered shared components. No scope is inferred, trimmed or case-normalized. Existing successful scoped resolutions and no-option summaries are preserved.
