# Bounded declarative action model

`glca.transitions` expands caller-declared puzzle/state rules into an explicit graph and reuses `glca.retail.solve_model` and the existing GLCA reachability implementation. It is not a scheduler, native executor, symbolic binary interpreter or authenticated gameplay oracle.

Inputs are a versioned `OpenRemaster.RLR.ActionModel.v1`, an exact project-scoped typed state and a matching source manifest. Each action and terminal predicate requires source-file hashes and byte-range references. Source references bind the supplied declaration; they do not prove that its guard/effect semantics match the original executable.

Guards use strict typed equality and explicit three-valued handling. Unknown guards never enable an action. Unknown terminal predicates prevent a claimed completion. Conflicting known success/failure predicates are rejected. Effects can set supplied state values or delete known dictionary entries; they cannot invoke code, shell commands, processes or files. Missing effect targets remain unknown rather than inventing containers.

Exploration is deterministic and bounded by states, transitions, declared action/predicate evaluations and aggregate encoded state bytes. State identities preserve actor/item ownership, object values, timers and explicit unknowns through the v005 canonical-state helper. No-op cycles deduplicate. Output witnesses retain action IDs and source-reference digests. Repeated source references are stored once in an action-source table.

`action_model_atlas` projects the result through the existing source-bound atlas contract. Missing predicates, unknown branches or exhausted bounds prevent proof of closure; no confirmed original softlock, authentic ending, native save roundtrip or game fidelity is asserted. All results remain STATIC_CANDIDATE with dispatch/release disabled. Existing K003/Owner/Governor and production gates are unchanged.

Tests use only synthetic resources and declared model facts. An independently admitted game adapter and authentic original/remaster traces are still required before adopting real game semantics.
