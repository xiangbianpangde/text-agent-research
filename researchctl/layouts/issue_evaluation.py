"""Read-only, version-pinned disposition sidecar verification; never writes a registry."""

from __future__ import annotations

from .research_tool import require, digest, sha, json_text, object_value, text


def verify(evaluation, graph=None, inputs=None):
    try:
        return _verify(evaluation, graph, inputs)
    except (KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
        from .research_tool import LayoutError

        if isinstance(exc, LayoutError):
            raise
        raise LayoutError("malformed issue evaluation or ledger record") from exc


def _verify(evaluation, graph=None, inputs=None):
    object_value(evaluation, "issue evaluation")
    require(evaluation.get("schema") == "issue-evaluation/v1", "unknown issue evaluation schema")
    head = digest(evaluation.get("issue_head_sha256"), "issue HEAD")
    require(
        evaluation.get("hard_evidence_checks_waivable") is False, "source checks cannot be waived"
    )
    ledger = object_value(evaluation.get("decision_snapshot"), "decision snapshot")
    require(
        set(ledger)
        == {
            "schema",
            "head_sha256",
            "registry_id",
            "state_sha256",
            "state",
            "revisions",
            "evidence_artifacts",
        }
        and ledger["schema"] == "issue-ledger-snapshot/v1",
        "unknown decision snapshot schema",
    )
    require(
        ledger["head_sha256"] == head and ledger["registry_id"] == evaluation["registry_id"],
        "decision snapshot identity mismatch",
    )
    state = object_value(ledger["state"], "decision state")
    require(
        sha(json_text(state).encode()) == digest(ledger["state_sha256"], "decision state"),
        "decision state digest mismatch",
    )
    require(
        state.get("schema") == "issue-state/v1"
        and state.get("registry_id") == evaluation["registry_id"],
        "unknown decision state identity",
    )
    revisions = object_value(ledger["revisions"], "ledger revisions")
    require(
        head in revisions and revisions[head].get("state_sha256") == ledger["state_sha256"],
        "decision state is not bound to committed HEAD",
    )
    seen, event_ids, keys, chain, pins, pin = set(), set(), set(), [], [], head
    while pin is not None:
        digest(pin, "ledger revision")
        require(pin not in seen and pin in revisions, "broken/cyclic issue revision chain")
        seen.add(pin)
        revision = object_value(revisions[pin], "ledger revision")
        require(
            set(revision) == {"schema", "previous", "event", "state_sha256"}
            and revision["schema"] == "issue-revision/v1",
            "unknown issue revision schema",
        )
        require(sha(json_text(revision).encode()) == pin, "issue revision hash mismatch")
        event = object_value(revision["event"], "ledger event")
        require(
            set(event)
            == {
                "event_id",
                "type",
                "payload",
                "request",
                "idempotency_key",
                "request_sha256",
                "actor_label",
                "actor_authority",
                "timestamp_utc",
                "receipt",
            },
            "unknown issue event fields",
        )
        require(event["actor_authority"] == "self_asserted_agent", "unverified event authority")
        require(
            event["event_id"] not in event_ids and event["idempotency_key"] not in keys,
            "duplicate ledger event/key",
        )
        event_ids.add(text(event["event_id"], "event ID"))
        keys.add(text(event["idempotency_key"], "event key"))
        request = {
            "type": event["type"],
            "payload": event["request"],
            "actor": event["actor_label"],
        }
        require(
            sha(json_text(request).encode()) == event["request_sha256"],
            "ledger request digest mismatch",
        )
        receipt = event["receipt"]
        require(
            receipt.get("event_id") == event["event_id"]
            and receipt.get("event_type") == event["type"]
            and receipt.get("payload_sha256") == sha(json_text(event["payload"]).encode()),
            "ledger receipt mismatch",
        )
        chain.append(event)
        pins.append(pin)
        pin = revision["previous"]
    require(seen == set(revisions), "unreachable ledger revisions in snapshot")
    require(chain[-1]["type"] == "initialize", "ledger missing initialization")
    from .issue_ledger import replay, effective

    replayed = None
    for revision_pin, event in zip(reversed(pins), reversed(chain)):
        replayed = replay(replayed, event)
        require(
            sha(json_text(replayed).encode()) == revisions[revision_pin]["state_sha256"],
            "ledger intermediate replay state mismatch",
        )
    require(replayed == state, "HEAD decision state differs from full replay")
    artifacts = object_value(ledger["evidence_artifacts"], "ledger evidence artifacts")
    for artifact_pin, data in artifacts.items():
        require(
            isinstance(data, str) and sha(data.encode()) == artifact_pin,
            "ledger evidence artifact hash mismatch",
        )
    from .issue_evidence import verify_origins, verify_imports

    verify_imports(chain, artifacts)
    verify_origins(state, artifacts)
    effective_state = effective(state)
    issues = list(effective_state["issues"].values())
    closed = [i for i in issues if i["effective_lifecycle"] == "closed"]
    active = [i for i in issues if i["effective_lifecycle"] != "closed"]
    expected_counts = {
        "original_observations": len(state["observations"]),
        "atomic_issues": len(issues),
        "required_unresolved": sum(i["required"] for i in active),
        "open": len(active),
        "closed": len(closed),
        "constraints": sum(c["applicability"] == "active" for c in state["constraints"].values()),
        "administratively_disposed": len(closed),
        "scientifically_answered": sum(i["scientific_answered"] for i in closed),
        "new_scientific_evidence_added": sum(i["new_scientific_evidence_added"] for i in closed),
    }
    require(
        evaluation.get("counts") == expected_counts, "evaluation counts differ from verified state"
    )
    expected_active = [i for i in active if i["required"]]
    supplied_active = evaluation.get('active_required_issues')
    require(isinstance(supplied_active, list)
            and len({i['issue_id'] for i in supplied_active}) == len(supplied_active),
            'invalid or duplicate active requirements')
    require(
        {i['issue_id']: i for i in supplied_active}
        == {i['issue_id']: i for i in expected_active},
        "evaluation hides or invents active requirements",
    )
    require(
        evaluation.get("new_scientific_evidence_added")
        == expected_counts["new_scientific_evidence_added"],
        "new evidence count differs from verified state",
    )
    network, policy = None, None
    proposals, reviews = {}, set()
    for event in reversed(chain):
        kind, data = event["type"], event["payload"]
        require(
            kind
            in {
                "initialize",
                "import",
                "propose",
                "review",
                "network_propose",
                "network_review",
                "checkpoint",
            },
            "unknown ledger event type",
        )
        if kind in {"propose", "network_propose"}:
            proposal = data["proposal"]
            require(proposal["proposal_id"] not in proposals, "duplicate proposal")
            proposals[proposal["proposal_id"]] = proposal
        if kind in {"review", "network_review"}:
            proposal = proposals.get(data["proposal_id"])
            require(
                proposal is not None and data["proposal_id"] not in reviews,
                "unknown/reviewed proposal",
            )
            reviews.add(data["proposal_id"])
            require(
                data["proposal_sha256"] == sha(json_text(proposal).encode()),
                "reviewed proposal changed",
            )
            require(
                type(data["approve"]) is bool and data["authority"] == "agent_source_review",
                "unsupported issue reviewer authority",
            )
            if kind == "network_review" and data["approve"]:
                require(
                    proposal["previous_network_sha256"] == sha(json_text(network).encode())
                    and proposal["previous_policy_sha256"] == sha(json_text(policy).encode()),
                    "stale network decision",
                )
                network, policy = proposal["network"], proposal["policy"]
    require(
        network == state["network"] and policy == state["policy"],
        "state network differs from reviewed history",
    )
    require(
        evaluation.get("network_sha256") == sha(json_text(network).encode())
        and evaluation.get("policy_sha256") == sha(json_text(policy).encode()),
        "issue map/policy version mismatch",
    )
    for key in [
        "required_unresolved_total",
        "required_unresolved_high",
        "new_scientific_evidence_added",
    ]:
        require(
            type(evaluation.get(key)) is int and evaluation[key] >= 0,
            "invalid issue evaluation count",
        )
    require(
        evaluation["required_unresolved_high"] <= evaluation["required_unresolved_total"],
        "issue high exceeds total",
    )
    required = evaluation.get("active_required_issues")
    require(
        isinstance(required, list) and len({i["issue_id"] for i in required}) == len(required),
        "invalid/duplicate active issues",
    )
    require(
        evaluation["required_unresolved_total"] >= len(required),
        "issue count hides active requirements",
    )
    from .issue_projection import verify_projection

    verify_projection(evaluation, effective_state, graph, inputs, artifacts)
    require(
        evaluation.get("network_assessment") is None
        or (
            evaluation["network_assessment"].get("network_sha256") == evaluation["network_sha256"]
            and evaluation["network_assessment"].get("policy_sha256") == evaluation["policy_sha256"]
            and evaluation["network_assessment"].get("automatic_issue_closures") == 0
            and evaluation["network_assessment"].get("new_scientific_evidence_added") == 0
        ),
        "network assessment identity/progress mismatch",
    )
