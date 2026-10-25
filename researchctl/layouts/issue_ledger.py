"""Pure read-only replay for the producer's issue-ledger/v1; no storage or writes."""

from __future__ import annotations
import copy

from .research_tool import require, sha, json_text


def pin(value):
    return sha(json_text(value).encode())


def _request_binding(kind, request, data):
    require(isinstance(request, dict), "invalid ledger request")
    if kind in {"initialize", "checkpoint"}:
        require(request == data, "request/payload mismatch")
    elif kind == "import":
        require(set(request) == {"root_id", "run_id", "audit_sha256"}, "invalid import request")
        require(
            all(
                o["origin"]["root_id"] == request["root_id"]
                and o["origin"]["run_id"] == request["run_id"]
                and o["origin"]["artifact_sha256"] == request["audit_sha256"]
                for o in data["observations"]
            ),
            "import request identity mismatch",
        )
    elif kind == "network_propose":
        require(
            set(request) == {"network", "policy"}
            and request == {k: data["proposal"][k] for k in request},
            "network proposal request mismatch",
        )
    elif kind in {"review", "network_review"}:
        expected = {"proposal_id", "proposal_sha256", "approve", "reason", "authority"}
        if kind == "network_review":
            expected.add("reviewer_label")
        require(
            set(request) == expected and all(data[k] == value for k, value in request.items()),
            "review request decision mismatch",
        )


def context(state, issue):
    return pin(
        {
            "scope": issue["scope"],
            "origins": [state["observations"][oid]["origin"] for oid in issue["origin_ids"]],
            "network": pin(state["network"]),
            "policy": pin(state["policy"]),
        }
    )


def replay(state, event):
    kind, data = event["type"], event["payload"]
    _request_binding(kind, event["request"], data)
    if kind == "initialize":
        require(
            state is None and set(data) == {"registry_id", "roots"}, "invalid ledger initialization"
        )
        return {
            "schema": "issue-state/v1",
            "registry_id": data["registry_id"],
            "roots": data["roots"],
            "observations": {},
            "issues": {},
            "constraints": {},
            "proposals": {},
            "network_proposals": {},
            "history": [],
            "network": None,
            "policy": None,
        }
    require(state is not None, "missing ledger initialization")
    state = copy.deepcopy(state)
    if kind == "import":
        for observation in data["observations"]:
            oid = observation["occurrence_id"]
            require(
                oid == "OBS-" + pin(observation["origin"])
                and pin(observation["original"]) == observation["origin"]["value_sha256"],
                "invalid imported observation",
            )
            if oid in state["observations"]:
                require(state["observations"][oid] == observation, "conflicting observation")
                continue
            state["observations"][oid] = observation
            question = (
                observation["original"].get("description", "")
                if isinstance(observation["original"], dict)
                else observation["original"]
            )
            scope = {
                k: (
                    "original_observation_review"
                    if k == "purpose"
                    else question
                    if k == "target_requirement"
                    else "unknown"
                )
                for k in [
                    "purpose",
                    "population",
                    "challenge",
                    "intervention_condition",
                    "outcome",
                    "time_window",
                    "denominator_unit",
                    "target_requirement",
                ]
            }
            iid = "ISS-" + pin([state["registry_id"], oid])[:32]
            state["issues"][iid] = {
                "issue_id": iid,
                "origin_ids": [oid],
                "scope": scope,
                "required": observation["required"],
                "kind": "unclassified",
                "revision": 1,
                "lifecycle": "open",
                "assessment": "unassessed",
                "resolution": None,
                "scientific_answered": False,
                "new_scientific_evidence_added": False,
                "children": [],
                "links": [],
                "pending_proposal_id": None,
            }
    elif kind == "propose":
        p = data["proposal"]
        issue = state["issues"][p["issue_id"]]
        from .issue_rules import transition

        transition(state, issue, p["operation"], p["payload"])
        require(
            p["proposal_id"] not in state["proposals"]
            and issue["revision"] == p["issue_revision"]
            and issue["pending_proposal_id"] is None
            and context(state, issue) == p["context_sha256"],
            "invalid issue proposal sequence/context",
        )
        require(
            event["request"]
            == {
                "issue_id": p["issue_id"],
                "operation": p["operation"],
                "revision": p["issue_revision"],
                "payload": p["payload"],
            },
            "proposal request mismatch",
        )
        issue["lifecycle_before_proposal"] = issue["lifecycle"]
        issue.update(
            lifecycle="pending_review",
            pending_proposal_id=p["proposal_id"],
            revision=issue["revision"] + 1,
        )
        state["proposals"][p["proposal_id"]] = p
    elif kind == "review":
        p = state["proposals"][data["proposal_id"]]
        issue = state["issues"][p["issue_id"]]
        require(
            issue["pending_proposal_id"] == p["proposal_id"]
            and issue["revision"] == p["issue_revision"] + 1
            and data["proposal_sha256"] == pin(p)
            and data["context_sha256"] == p["context_sha256"],
            "invalid issue review sequence",
        )
        issue["lifecycle"] = issue.pop("lifecycle_before_proposal")
        if data["approve"]:
            require(context(state, issue) == p["context_sha256"], "stale issue review context")
            op, payload = p["operation"], p["payload"]
            from .issue_rules import transition

            transition(state, issue, op, payload)
            if op == "revalidate":
                issue["last_revalidation"] = data
            elif op == "classify":
                issue.update(
                    kind=payload["kind"],
                    scope=payload["scope"],
                    lifecycle="working",
                    classification_reopened=False,
                )
            elif op == "assess":
                issue.update(assessment=payload["assessment"], lifecycle="working")
            elif op == "link_history":
                hid = "HIS-" + pin(p)[:32]
                state.setdefault("history_links", {})[hid] = {
                    "history_link_id": hid,
                    "issue_id": issue["issue_id"],
                    "origin_ids": issue["origin_ids"],
                    "relation": payload["relation"],
                    "target_ref": payload["target_ref"],
                    "evidence_refs": payload["evidence_refs"],
                    "reviewed_proposal_sha256": pin(p),
                }
            elif op == "reopen":
                issue.update(
                    lifecycle="working",
                    resolution=None,
                    scientific_answered=False,
                    new_scientific_evidence_added=False,
                    classification_reopened=True,
                    links=[],
                )
                for c in state["constraints"].values():
                    if c["issue_id"] == issue["issue_id"]:
                        c["applicability"] = "superseded"
            else:
                require(
                    op
                    in {
                        "resolved",
                        "corrected",
                        "duplicate",
                        "decomposed",
                        "out_of_scope",
                        "superseded",
                        "reclassified_constraint",
                    },
                    "unknown disposition operation",
                )
                issue.update(
                    lifecycle="closed",
                    resolution=op,
                    scientific_answered=payload.get("scientific_answered", False),
                    new_scientific_evidence_added=payload.get(
                        "new_scientific_evidence_added", False
                    ),
                )
                if op == "decomposed":
                    for index, part in enumerate(payload["parts"]):
                        child = copy.deepcopy(issue)
                        for field in [
                            "last_decision",
                            "decision_scope_sha256",
                            "decision_network_sha256",
                            "decision_policy_sha256",
                        ]:
                            child.pop(field, None)
                        cid = "ISS-" + pin([p["proposal_id"], index])[:32]
                        child.update(
                            issue_id=cid,
                            scope=part["scope"],
                            revision=1,
                            lifecycle="open",
                            assessment="unassessed",
                            resolution=None,
                            children=[],
                            links=[],
                            pending_proposal_id=None,
                        )
                        state["issues"][cid] = child
                        issue["children"].append(cid)
                elif op in {"duplicate", "superseded"}:
                    issue["links"].append({"kind": op, "target": payload["target_issue_id"]})
                elif op == "reclassified_constraint":
                    cid = "CON-" + pin(p)[:32]
                    state["constraints"][cid] = {
                        "constraint_id": cid,
                        "issue_id": issue["issue_id"],
                        "scope": issue["scope"],
                        "origin_ids": issue["origin_ids"],
                        "evidence_refs": payload["evidence_refs"],
                        "applicability": "active",
                    }
            if op not in {"link_history", "revalidate"}:
                issue["last_decision"] = data
            if op != "link_history":
                issue.update(
                    decision_scope_sha256=pin(issue["scope"]),
                    decision_network_sha256=pin(state["network"]),
                    decision_policy_sha256=pin(state["policy"]),
                )
        else:
            issue["lifecycle"] = "working" if issue["lifecycle"] != "closed" else "closed"
        issue["pending_proposal_id"] = None
        issue["revision"] += 1
        state["history"].append(data)
    elif kind == "checkpoint":
        state["history"].append({"kind": "checkpoint", "reason": data["reason"]})
    elif kind == "network_propose":
        p = data["proposal"]
        require(
            p["proposal_id"] not in state["network_proposals"]
            and p["previous_network_sha256"] == pin(state["network"])
            and p["previous_policy_sha256"] == pin(state["policy"]),
            "invalid network proposal context",
        )
        state["network_proposals"][p["proposal_id"]] = p
    elif kind == "network_review":
        p = state["network_proposals"][data["proposal_id"]]
        require(
            not any(x.get("proposal_id") == data["proposal_id"] for x in state["history"]),
            "repeated network review",
        )
        require(data["proposal_sha256"] == pin(p), "network proposal hash mismatch")
        if data["approve"]:
            require(
                p["previous_network_sha256"] == pin(state["network"])
                and p["previous_policy_sha256"] == pin(state["policy"]),
                "stale network review",
            )
            state["network"], state["policy"] = p["network"], p["policy"]
        state["history"].append(data)
    else:
        require(False, "unknown ledger event")
    return state


def effective(state):
    result = copy.deepcopy(state)
    for issue in result["issues"].values():
        changed = bool(
            issue.get("last_decision")
            and (
                issue.get("decision_scope_sha256") != pin(issue["scope"])
                or issue.get("decision_network_sha256") != pin(state["network"])
                or issue.get("decision_policy_sha256") != pin(state["policy"])
            )
        )
        issue.update(
            needs_revalidation=changed,
            effective_lifecycle="open" if changed else issue["lifecycle"],
        )
    return result
