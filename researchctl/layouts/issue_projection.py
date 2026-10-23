"""Recompute issue-evaluation/v1 counts from verified state and exact current findings."""

from __future__ import annotations
from .research_tool import require
from .issue_ledger import pin


def leaves(state, candidates):
    result, pending, seen = {}, list(candidates), set()
    while pending:
        issue = pending.pop()
        if issue["issue_id"] in seen:
            continue
        seen.add(issue["issue_id"])
        if issue["effective_lifecycle"] == "closed" and issue["resolution"] in {
            "duplicate",
            "superseded",
        }:
            pending.extend(state["issues"][link["target"]] for link in issue["links"])
        elif issue["effective_lifecycle"] == "closed" and issue["resolution"] == "decomposed":
            pending.extend(state["issues"][cid] for cid in issue["children"])
        else:
            result[issue["issue_id"]] = issue
    return list(result.values())


def verify_projection(evaluation, state, graph, inputs=None, artifacts=None):
    findings = evaluation.get("raw_findings")
    require(isinstance(findings, list), "raw issue findings missing")
    by_record = {}
    for observation in state["observations"].values():
        if observation["kind"] == "finding":
            by_record.setdefault(pin(observation["original"]), []).append(observation)
    unresolved, represented, corrected, matched = [], set(), [], set()
    for finding in findings:
        choices = by_record.get(pin(finding), [])
        if not choices:
            unresolved.append(finding)
            continue
        matched.update(o["occurrence_id"] for o in choices)
        candidates = leaves(
            state,
            [
                i
                for i in state["issues"].values()
                if any(o["occurrence_id"] in i["origin_ids"] for o in choices)
            ],
        )
        active = [i for i in candidates if i["effective_lifecycle"] != "closed"]
        decisions = [
            i
            for i in candidates
            if i["resolution"] in {"corrected", "resolved"} and not i["needs_revalidation"]
        ]
        if active or not candidates or len(decisions) != len(candidates):
            unresolved.append(finding)
            if any(i["required"] for i in active):
                represented.add(pin(finding))
        else:
            corrected.append(finding["finding_id"])
    required = [
        i
        for i in state["issues"].values()
        if i["required"] and i["effective_lifecycle"] != "closed"
    ]
    unmatched = [f for f in unresolved if pin(f) not in represented]
    limits = evaluation.get("unmatched_current_limitations")
    require(
        isinstance(limits, list) and all(isinstance(t, str) for t in limits),
        "invalid unmatched limitations",
    )
    imported_limits = {
        pin(o["original"]) for o in state["observations"].values() if o["kind"] == "limitation"
    }
    require(
        all(pin(t) not in imported_limits for t in limits),
        "unmatched limitation already represented",
    )
    if inputs is not None:
        require(
            findings == inputs.get("raw_findings"), "evaluation omitted committed current finding"
        )
        current_limits = inputs.get("known_limitations")
        require(
            isinstance(current_limits, list)
            and limits == [t for t in current_limits if pin(t) not in imported_limits],
            "evaluation omitted current limitation",
        )
    total = len(required) + len(unmatched) + len(limits)
    high = sum(
        any(
            isinstance(state["observations"][oid]["original"], dict)
            and state["observations"][oid]["original"].get("priority") == "high"
            for oid in i["origin_ids"]
        )
        for i in required
    )
    high += sum(f["priority"] == "high" for f in unmatched)
    require(
        evaluation.get("required_unresolved_total") == total
        and evaluation.get("required_unresolved_high") == high,
        "evaluated required counts differ from replayed obligations",
    )
    require(
        evaluation.get("reviewed_unresolved_findings") == unresolved
        and evaluation.get("corrected_original_ids") == corrected
        and evaluation.get("matched_occurrence_ids") == sorted(matched),
        "evaluated finding projection differs",
    )
    require(
        evaluation.get("constraints") == list(state["constraints"].values()),
        "constraint projection differs",
    )
    require(
        evaluation.get("history_links", []) == list(state.get("history_links", {}).values()),
        "history projection differs",
    )
    if graph is not None:
        facts = {f["claim_id"]: f for f in graph["facts"]}
        source_versions = {s["source_id"]: s["content_sha256"] for s in graph["sources"]}
        for issue in state["issues"].values():
            if issue["effective_lifecycle"] != "closed" or issue["resolution"] not in {
                "corrected",
                "resolved",
            }:
                continue
            proposal = state["proposals"][issue["last_decision"]["proposal_id"]]
            for ref in proposal["payload"].get("evidence_refs", []):
                if "claim_id" not in ref:
                    continue
                require(ref["claim_id"] in facts, "closure evidence missing from current graph")
                from .issue_evidence import reference_value

                reviewed = reference_value(artifacts, ref)
                current = facts[ref["claim_id"]]
                require(
                    reviewed["text"] == current["text"]
                    and reviewed["citations"] == current["citations"],
                    "current closure claim differs from reviewed source version",
                )
                require(
                    all(
                        source_versions.get(c["source_id"]) == c["content_sha256"]
                        for c in facts[ref["claim_id"]]["citations"]
                    ),
                    "closure source differs from current graph",
                )
