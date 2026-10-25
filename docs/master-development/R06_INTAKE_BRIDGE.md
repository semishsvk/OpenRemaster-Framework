# R06 intake integration with the master advisory workflow

The bridge consumes `OpenRemaster.R06.LiveAuthorityIntakeReport.v1`, the existing R06 validator's output. It is not another admission service, signature verifier or scheduler. It does not follow report-supplied paths, read credentials, acquire leases, start workers or dispatch.

`advisory_package` now accepts optional `intake_report` and `intake_context`. The caller supplies the exact operation, WorkPackage digest, project, capability and packet digest. Mismatched projects, missing bindings, contradictory summaries, incomplete checks and unknown authority flags stay HOLD or REJECT. Combined and separate Owner/Witness report shapes are supported. Manifest claims must also be structurally complete.

Even a complete, self-declared PASS report remains **HOLD** with `independent_authority_verified=false`. The existing R06 validator does not perform cryptographic verification; its claims cannot transfer authority. Fresh independent crypto, current owner/writer lease, K003 admission and Resource Governor revalidation remain separate requirements.

The optional bounded file reader requires an exact supplied SHA-256, rejects duplicate JSON keys and non-finite values, and does not modify the selected snapshot. A matching digest proves byte identity only.

New intake observations and DEV receipt changes participate in the proposal digest, preventing stale advisory cache reuse after their evidence changes. Calls with neither new intake nor DEV receipt retain their previous proposal digest. Existing no-dispatch behavior and zero-heavy-slot proposals are unchanged.

Nineteen new test methods exercise binding, contradictory/forged claims, schema/type failures, combined/separate principals, input integrity and compatibility. These are source/synthetic tests, not independent production validation. The original report's missing real external receipts remain an explicit HOLD.
