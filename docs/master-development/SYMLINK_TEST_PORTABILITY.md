# Windows symlink test investigation

The original sandbox command was `python -B -m pytest tests -q` from the isolated integration checkout, using the workspace's scoped pytest dependencies. The original full run produced 971 PASS and one failure at `Path.symlink_to`, with Windows error 1314 (`A required privilege is not held by the client`). The recovery constructor had not yet executed.

This distinguishes unavailable fixture setup from a demonstrated security regression. The original real-filesystem symlink rejection test remains present. It skips only error 1314 during symlink creation, with an explicit message that real filesystem rejection remains unverified on this identity. Other setup errors propagate as failures. On a symlink-capable environment it still requires `RecoveryHold('refusing symlinked ledger')` and checks that the outside target is unchanged.

Separate unit tests simulate the detection result to ensure rejection occurs before SQLite is opened. They do not claim real OS symlink verification. Additional tests exercise the exact missing-privilege skip and ensure generic errors and Windows Access Denied (5) are not skipped.

No recovery implementation, owner admission, worker isolation, signing authority, ACL, system security setting or sandbox configuration was changed. Subsequent verification remained inside the sandbox. The targeted recovery suite produced 44 PASS and one explicitly reported SKIP.

Full local commands, original failure details and JUnit evidence are retained in the private master v002 record. Linux CI retains the real filesystem security test; no Linux result is claimed until an actual CI run completes.
