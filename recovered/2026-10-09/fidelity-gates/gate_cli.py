"""Read-only contract gate CLI. Exit 0 only on allowed/validated contract outcomes.

Never writes canonical sources or changes ORCH-K003/worker state.
"""
import argparse
import json
from pathlib import Path
import sys

from alignment import admissibility
from semantics import resolve_resources, validate_population
from causal import analyze_causes, promotion_readiness


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def run():
    parser = argparse.ArgumentParser(description="OpenRemaster isolated fidelity contract validation")
    parser.add_argument("mode", choices=("alignment", "resources", "population", "causal", "promotion"))
    parser.add_argument("manifest")
    parser.add_argument("--original-root")
    parser.add_argument("--reconstruction-root")
    parser.add_argument("--policy-root")
    parser.add_argument("--evidence-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    data = load_json(args.manifest)
    if args.mode == "alignment":
        roots = None
        if args.original_root and args.reconstruction_root and args.policy_root:
            roots = {"original": args.original_root, "reconstruction": args.reconstruction_root,
                     "policy": args.policy_root}
        result = admissibility(data, roots)
        allowed = result["status"] == "ADMISSIBLE"
    elif args.mode == "resources":
        result = resolve_resources(data, data.get("requested", []), args.evidence_root)
        allowed = result["status"] == "RESOLUTION_CONTRACT_PASS"
    elif args.mode == "population":
        result = validate_population(data, args.evidence_root)
        allowed = result["status"] == "POPULATION_CONTRACT_PASS"
    elif args.mode == "causal":
        result = analyze_causes(data.get("admission"), data.get("observations"))
        allowed = result["status"] == "EVALUATED"
    else:
        result = promotion_readiness(data.get("admission"), data.get("comparison"))
        allowed = result["status"] in ("ELIGIBLE_FOR_EXTERNAL_ACCEPTANCE",
                                       "VALID_FIDELITY_FAIL")
    wire = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    print(wire)
    if args.output:
        path = Path(args.output).resolve()
        lowered = str(path).lower().replace("/", "\\")
        if "\\remaster framework\\source\\" in lowered:
            raise ValueError("WRITES_TO_CANONICAL_SOURCE_FORBIDDEN")
        if not path.parent.is_dir():
            raise ValueError("OUTPUT_PARENT_MISSING")
        path.write_text(wire + "\n", encoding="utf-8")
    return 0 if allowed else 2


if __name__ == "__main__":
    try:
        sys.exit(run())
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "FidelityGateCLIError.v1",
                          "status": "FAIL", "error": type(exc).__name__,
                          "detail": str(exc)}), file=sys.stderr)
        sys.exit(3)
