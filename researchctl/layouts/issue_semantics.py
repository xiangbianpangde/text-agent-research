"""Read-only identity binding of report semantic interpretation to the reviewed decision map."""
from __future__ import annotations
from .research_tool import require


def verify_semantics(packet, evaluation, graph):
    require(isinstance(packet, dict) and packet.get('schema') == 'reviewed-report-semantics/v1',
            'unknown reviewed report semantics')
    require(all(packet.get(k) == evaluation.get(k)
                for k in ['registry_id','issue_head_sha256','network_sha256','policy_sha256']),
            'report semantic versions differ from reviewed disposition')
    network = evaluation['decision_snapshot']['state']['network']
    require(network is not None and all(packet.get(k) == network.get(k)
                                       for k in ['assignments','edges','studies']),
            'report semantic scope/role map differs from reviewed network')
    mapped = {a['claim_id'] for a in network['assignments']}
    require(packet.get('unmapped_claim_ids') == sorted({f['claim_id'] for f in graph['facts']} - mapped),
            'report semantic coverage omits or invents mapping')
    require(packet.get('interpretations_are_not_new_source_evidence') is True,
            'semantic mapping cannot count as original scientific evidence')
    assessment = packet.get('assessment')
    require(isinstance(assessment, dict)
            and assessment.get('network_sha256') == evaluation['network_sha256']
            and assessment.get('policy_sha256') == evaluation['policy_sha256'],
            'report semantic assessment version mismatch')
