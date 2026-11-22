"""Game-neutral discovery contract plus a narrow OpenZak decoded-source adapter."""
from collections import Counter, defaultdict
from .core import require


def discover(project, objects, effects, source_pins):
    require(bool(project) and bool(source_pins), "SOURCE_IDENTITY_REQUIRED")
    rooms = sorted({o["room"] for o in objects if type(o.get("room")) is int})
    kinds = Counter(e["kind"] for e in effects)
    return {"project": project, "status": "SOURCE_ONLY", "source_pins": source_pins,
            "rooms": rooms, "objects": len(objects), "programs_with_effects": len({e["program"] for e in effects}),
            "effects": len(effects), "effect_kinds": dict(kinds),
            "actors": "PARTIAL_OPERAND_REFERENCES", "inventory": "OWNERSHIP_NOT_RESOLVED",
            "camera": {k: v for k, v in kinds.items() if "camera" in k.lower()},
            "unknowns": ["VICTORY_PREDICATE", "EXECUTION_ORDER", "GUARD_SEMANTICS",
                         "ACTOR_IDENTITY_AND_OWNERSHIP", "TIMING", "SAVE_LOAD", "FULL_CORPUS_COVERAGE"],
            "full_game_validated": False}


def decoded_cfg(programs, max_instructions=100000):
    """Candidate CFG retaining raw guard operands; no instruction semantics invented.

    Branch target and fallthrough are static alternatives. Calls are dependencies,
    not unconditional execution edges. Undecoded bytes and scheduler semantics stay unknown.
    """
    require(sum(len(p["instructions"]) for p in programs) <= max_instructions, "INSTRUCTION_BOUND")
    nodes, edges, calls, unknowns, terminals = [], [], [], [], []
    for program in programs:
        key = program["key"]
        pcs = {i["pc"] for i in program["instructions"]}
        require(len(pcs) == len(program["instructions"]), "DUPLICATE_PC")
        if program.get("status") != "STATIC_COMPLETE_CANDIDATE":
            unknowns.append({"program": key, "reason": "PARTIAL_DECODE", "status": program.get("status")})
        for ins in program["instructions"]:
            ident = f"{key}:{ins['pc']}"
            kind, operands = ins["kind"], ins.get("operands", {})
            nodes.append({"id": ident, "program": key, "source": {"file": program.get("file"),
                          "offset": program.get("offset"), "sha256": program.get("sha256")}, **ins})
            targets = []
            branch = operands.get("branch_to_pc")
            if branch is not None:
                targets.append((branch, "BRANCH_ALTERNATIVE"))
            if kind not in {"relativeJump", "stopObjectCode", "chainScript"}:
                targets.append((ins["end_pc"], "FALLTHROUGH_CANDIDATE"))
            for pc, role in targets:
                if pc in pcs:
                    edges.append({"from": ident, "to": f"{key}:{pc}", "role": role,
                                  "guard": None, "raw_operands": operands})
                elif pc != program.get("bytes"):
                    unknowns.append({"program": key, "pc": ins["pc"], "target": pc, "reason": "UNDECODED_TARGET"})
            if kind in {"startScript", "chainScript", "stopScript", "startObject"}:
                calls.append({"from": ident, "kind": kind, "operands": operands,
                              "execution_proven": False})
            if kind == "systemOps":
                terminals.append({"program": key, "pc": ins["pc"], "operands": operands,
                                  "status": "STATIC_CANDIDATE", "victory_verified": False})
    return {"status": "SOURCE_ONLY", "nodes": nodes, "edges": edges,
            "script_dependencies": calls, "unknowns": unknowns,
            "terminal_operation_candidates": terminals, "victory_predicate": "UNKNOWN",
            "conditional_cfg_executed": False, "runtime_verified": False}


def reverse_script_dependencies(programs, seeds):
    reverse = defaultdict(set)
    for program in programs:
        for ins in program["instructions"]:
            if ins["kind"] in {"startScript", "chainScript"}:
                operand = ins.get("operands", {}).get("script", {})
                if type(operand.get("direct")) is int:
                    reverse[f"SC{operand['direct']}"].add(program["key"])
    seen = set(seeds)
    pending = list(seeds)
    while pending:
        for parent in reverse[pending.pop()]:
            if parent not in seen:
                seen.add(parent)
                pending.append(parent)
    return {"seeds": seeds, "possible_prerequisite_programs": sorted(seen),
            "semantics": "STATIC_DIRECT_CALL_XREF_ONLY", "legal_completion_path_proven": False}
