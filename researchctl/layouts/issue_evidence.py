"""Pinned original audit and reviewed claim resolution from immutable embedded artifact bytes."""

from __future__ import annotations
import re
from .research_tool import require, _json, sha, json_text


def reference_value(artifacts, ref):
    common = {"root_id", "run_id", "path", "artifact_sha256", "run_record_sha256"}
    shape = common | ({"claim_id"} if "claim_id" in ref else {"json_pointer", "value_sha256"})
    require(set(ref) == shape, "unknown or mixed evidence reference fields")
    require(ref["artifact_sha256"] in artifacts, "missing embedded reviewed artifact")
    data = artifacts[ref["artifact_sha256"]].encode()
    require(sha(data) == ref["artifact_sha256"], "embedded artifact hash differs")
    value = _json(data, "issue evidence artifact")
    if "claim_id" in ref:
        facts = [f for f in value["facts"] if f["claim_id"] == ref["claim_id"]]
        require(len(facts) == 1, "reviewed claim missing/ambiguous in embedded graph")
        return facts[0]
    pointer = ref["json_pointer"]
    require(isinstance(pointer, str) and pointer.startswith("/"), "invalid original pointer")
    for item in pointer[1:].split("/"):
        require(not re.search(r"~(?![01])", item), "invalid JSON pointer escape")
        item = item.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            require(
                re.fullmatch(r"0|[1-9][0-9]*", item) and int(item) < len(value),
                "invalid JSON pointer array index",
            )
            value = value[int(item)]
        else:
            value = value[item]
    require(sha(json_text(value).encode()) == ref["value_sha256"], "original value hash differs")
    return value


def verify_imports(events, artifacts):
    for event in events:
        if event["type"] != "import":
            continue
        request = event["request"]
        require(request["audit_sha256"] in artifacts, "missing imported audit artifact")
        audit = _json(artifacts[request["audit_sha256"]].encode(), "imported original audit")
        expected = []
        for name, kind in [("unresolved_findings", "finding"), ("known_limitations", "limitation")]:
            require(isinstance(audit.get(name), list), "audit lacks original observation arrays")
            for index, value in enumerate(audit[name]):
                expected.append((kind, "/" + name + "/" + str(index), value))
        actual = event["payload"]["observations"]
        require(len(actual) == len(expected), "import omitted original audit obligations")
        for observation, (kind, pointer, value) in zip(actual, expected):
            require(
                observation["kind"] == kind
                and observation["origin"]["json_pointer"] == pointer
                and observation["original"] == value
                and observation["required"] is True,
                "import differs from complete original audit",
            )


def verify_origins(state, artifacts):
    refs = [r for p in state["proposals"].values() for r in p["payload"].get("evidence_refs", [])]
    refs += [r for p in state["network_proposals"].values() for r in p["network"]["evidence_refs"]]
    for ref in refs:
        require(ref["root_id"] in state["roots"], "unregistered evidence root")
        reference_value(artifacts, ref)
    for observation in state["observations"].values():
        ref = observation["origin"]
        require(
            set(ref)
            == {
                "root_id",
                "run_id",
                "path",
                "artifact_sha256",
                "run_record_sha256",
                "json_pointer",
                "value_sha256",
            },
            "invalid original-audit reference fields",
        )
        require(ref["root_id"] in state["roots"], "unregistered observation root")
        require(
            ref["path"] == f"runs/{ref['run_id']}/final/evidence-audit.json",
            "observation is not a canonical audit",
        )
        kind = observation["kind"]
        require(
            kind in {"finding", "limitation"} and observation["required"] is True,
            "imported requirement/type changed",
        )
        name = "unresolved_findings" if kind == "finding" else "known_limitations"
        import re

        require(
            re.fullmatch("/" + name + r"/(?:0|[1-9][0-9]*)", ref["json_pointer"]),
            "observation pointer/kind mismatch",
        )
        require(
            reference_value(artifacts, ref) == observation["original"],
            "observation differs from pinned original audit",
        )
