# Shadow test planning

The framework maps invalidated gameplay domains to a minimal advisory test plan.

## FAST
FAST suites are targeted checks for the invalidated domains. They are the default recommendation.

## VERIFY
VERIFY is recommended when integration-sensitive domains are impacted. In Phase 1 this remains advisory only: the framework cannot trigger, skip, cancel, or replace project validation.

## CANDIDATE
Candidate/release validation is intentionally outside Phase 1 planning. Existing project gates remain authoritative.

The planner is conservative: dependency propagation happens before suite selection, so a geometry change can select movement, transition, puzzle and save/load checks even when those files were not directly edited.
