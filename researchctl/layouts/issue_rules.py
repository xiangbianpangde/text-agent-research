"""Read-only validity constraints for applied issue-ledger/v1 disposition transitions."""

from __future__ import annotations
from .research_tool import require

ASSESSMENTS = {
    "unassessed",
    "partially_answered",
    "awaiting_material",
    "awaiting_data",
    "not_identifiable_under_scope",
}
RESOLUTIONS = {
    "resolved",
    "corrected",
    "duplicate",
    "decomposed",
    "out_of_scope",
    "superseded",
    "reclassified_constraint",
}
SCOPE = {
    "purpose",
    "population",
    "challenge",
    "intervention_condition",
    "outcome",
    "time_window",
    "denominator_unit",
    "target_requirement",
}


def scope(value):
    require(
        isinstance(value, dict)
        and set(value) == SCOPE
        and all(isinstance(v, str) and v.strip() for v in value.values()),
        "invalid issue scope",
    )


def transition(state, issue, operation, payload):
    extras = {
        "assess": {"assessment"},
        "classify": {"kind", "scope"},
        "reopen": set(),
        "link_history": {"relation", "target_ref"},
        "revalidate": {"prior_decision_sha256"},
        "decomposed": {"parts"},
        "duplicate": {"target_issue_id"},
        "superseded": {"target_issue_id"},
        "resolved": {"acceptance_met", "acceptance_evidence"},
        "corrected": set(),
        "out_of_scope": set(),
        "reclassified_constraint": set(),
    }
    require(
        operation in extras
        and isinstance(payload, dict)
        and set(payload)
        <= extras[operation]
        | {"rationale", "evidence_refs", "scientific_answered", "new_scientific_evidence_added"},
        "invalid disposition payload",
    )
    require(
        isinstance(payload.get("rationale"), str) and payload["rationale"].strip(),
        "missing disposition rationale",
    )
    refs = payload.get("evidence_refs", [])
    require(isinstance(refs, list), "invalid disposition references")
    answered, novel = (
        payload.get("scientific_answered", False),
        payload.get("new_scientific_evidence_added", False),
    )
    require(
        type(answered) is bool and type(novel) is bool and (not novel or answered),
        "invalid scientific flags",
    )
    require(
        not answered or (operation == "resolved" and issue["kind"] == "scientific_gap"),
        "invalid scientific answer",
    )
    require(
        issue["lifecycle"] == "closed"
        if operation == "reopen"
        else issue["lifecycle"] != "pending_review"
        if operation == "revalidate"
        else issue["lifecycle"] != "closed",
        "invalid lifecycle transition",
    )
    if operation == "revalidate":
        from .issue_ledger import pin

        prior = issue.get("last_decision")
        require(
            prior is not None and payload.get("prior_decision_sha256") == pin(prior),
            "revalidation prior decision mismatch",
        )
        original = state["proposals"][prior["proposal_id"]]
        require(
            refs == original["payload"].get("evidence_refs", []) and not answered and not novel,
            "revalidation replaces evidence/science",
        )
    if operation == "assess":
        require(payload.get("assessment") in ASSESSMENTS, "invalid assessment")
    if operation == "classify":
        require(
            issue["kind"] == "unclassified" or issue.get("classification_reopened", False),
            "issue already classified",
        )
        require(
            refs
            and payload["kind"]
            in {
                "report_wording",
                "representation",
                "scientific_gap",
                "source_conflict",
                "material_task",
                "persistent_constraint",
                "history",
            },
            "invalid classification",
        )
        require(
            issue["kind"] == "unclassified" or payload["kind"] == issue["kind"],
            "classification downgrades required kind",
        )
        scope(payload["scope"])
        require(
            payload["scope"]["purpose"] == payload["kind"]
            and payload["scope"]["target_requirement"] == issue["scope"]["target_requirement"],
            "classification rewrites requirement",
        )
        require(
            all(
                payload["scope"][k] == issue["scope"][k] or issue["scope"][k] == "unknown"
                for k in SCOPE - {"purpose"}
            ),
            "classification changes known scope",
        )
    if operation == "link_history":
        require(
            payload.get("relation") in {"related_to", "superseded_for_use"}
            and payload.get("target_ref") in refs,
            "invalid history link",
        )
    if "acceptance_evidence" in payload:
        acceptance = payload["acceptance_evidence"]
        require(
            isinstance(acceptance, list)
            and all(
                isinstance(row, dict)
                and set(row) == {"criterion", "evidence_ref"}
                and row["criterion"] == issue["scope"]["target_requirement"]
                and row["evidence_ref"] in refs
                for row in acceptance
            ),
            "invalid acceptance reference",
        )
    if operation in {"corrected", "resolved"}:
        require(
            refs and any("claim_id" in r for r in refs), "closure lacks committed claim evidence"
        )
        require(
            issue["assessment"]
            not in {"awaiting_data", "awaiting_material", "not_identifiable_under_scope"},
            "unanswered data requirement closed",
        )
        require(
            issue["kind"] in {"report_wording", "representation", "scientific_gap"}
            and issue["scope"]["purpose"] == issue["kind"],
            "unclassified scope closed",
        )
        if issue["kind"] == "scientific_gap":
            require(
                operation == "resolved"
                and answered
                and all(v != "unknown" for v in issue["scope"].values()),
                "unknown scientific question closed",
            )
            acceptance = payload.get("acceptance_evidence", [])
            require(
                len(acceptance) == 1
                and set(acceptance[0]) == {"criterion", "evidence_ref"}
                and acceptance[0]["criterion"] == issue["scope"]["target_requirement"]
                and acceptance[0]["evidence_ref"] in refs,
                "invalid scientific acceptance",
            )
        else:
            require(not answered and not novel, "wording adds science")
        if operation == "resolved":
            require(payload.get("acceptance_met") is True, "acceptance not met")
    if operation == "decomposed":
        parts = payload.get("parts", [])
        require(not issue["children"] and len(parts) >= 2, "invalid decomposition")
        for part in parts:
            require(
                set(part) == {"scope", "coverage_text"} and part["coverage_text"].strip(),
                "invalid atomic part",
            )
            scope(part["scope"])
            require(
                part["scope"]["target_requirement"] == part["coverage_text"]
                and all(
                    part["scope"][k] == issue["scope"][k] for k in SCOPE - {"target_requirement"}
                ),
                "decomposition changes scope",
            )
        require(
            "".join(p["coverage_text"] for p in parts) == issue["scope"]["target_requirement"],
            "incomplete requirement decomposition",
        )
    if operation in {"duplicate", "superseded"}:
        target = payload.get("target_issue_id")
        require(
            refs
            and issue["kind"] != "unclassified"
            and all(v != "unknown" for v in issue["scope"].values()),
            "unproven consolidation",
        )
        require(
            target in state["issues"] and target != issue["issue_id"], "invalid canonical target"
        )
        candidate = state["issues"][target]
        require(
            candidate["lifecycle"] not in {"closed", "pending_review"}
            and candidate["scope"] == issue["scope"]
            and candidate["kind"] == issue["kind"],
            "invalid target scope/lifecycle",
        )
        require(not issue["required"] or candidate["required"], "canonical loses requiredness")

        def high(item):
            return any(
                isinstance(state["observations"][oid]["original"], dict)
                and state["observations"][oid]["original"].get("priority") == "high"
                for oid in item["origin_ids"]
            )

        require(not high(issue) or high(candidate), "canonical loses priority")
        pending, seen = [target], set()
        while pending:
            current = pending.pop()
            require(current != issue["issue_id"], "issue replacement cycle")
            if current in seen:
                continue
            seen.add(current)
            pending.extend(state["issues"][current]["children"])
            pending.extend(x["target"] for x in state["issues"][current]["links"])
    if operation in {"out_of_scope", "reclassified_constraint"}:
        require(
            (
                not issue["required"]
                or operation == "reclassified_constraint"
                and issue["kind"] in {"persistent_constraint", "history"}
            )
            and refs,
            "required obligation removed",
        )
    if operation in {"duplicate", "superseded", "out_of_scope", "reclassified_constraint"}:
        require(
            not any(
                link["target"] == issue["issue_id"]
                for i in state["issues"].values()
                if i["resolution"] in {"duplicate", "superseded"}
                for link in i["links"]
            ),
            "canonical has dependent obligations",
        )
