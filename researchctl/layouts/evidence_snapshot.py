"""Report-independent, exact full-body queries over committed evidence snapshots."""
from __future__ import annotations

import re
from pathlib import Path

from .research_tool import (
    LayoutError, Snapshot, _span, digest, error_result, json_text, object_value,
    relative, require, sha, source_body,
)


def read_snapshot(root, path, expected_hash):
    snapshot = Snapshot(root)
    path = Path(path)
    if path.is_absolute():
        try:
            path = path.relative_to(Path(root).resolve())
        except ValueError as exc:
            raise LayoutError('evidence snapshot escapes root', 'UNSAFE_PATH') from exc
    path = relative(path.as_posix())
    payload = object_value(snapshot.json(path, digest(expected_hash, 'snapshot expected hash')), 'snapshot')
    rid = payload.get('run_id')
    require(payload.get('schema') == 'evidence-snapshot/v1' and re.fullmatch(r'[0-9a-f]{32}', str(rid)),
            'invalid evidence snapshot identity')
    require(path in {f'runs/{rid}/evidence-snapshot.json', f'runs/{rid}/evidence-initial.json'},
            'noncanonical snapshot path', 'UNSAFE_PATH')
    record_path = f'runs/{rid}/run-record.json'
    current = snapshot.json('runtime-state.json') if 'runtime-state.json' in snapshot.blobs else None
    if current is not None and current.get('run_id') == rid:
        state = current
    elif record_path in snapshot.blobs:
        state = snapshot.json(record_path)['runtime']
    else:
        raise LayoutError('snapshot run has no canonical runtime', 'SOURCE_UNAVAILABLE')
    require(state['run_id'] == rid and state['input_fingerprint'] == payload['input_fingerprint'],
            'evidence snapshot does not match actual runtime')
    pins = {}
    envelopes = {}
    for key, record in payload['stage_pins'].items():
        require(re.fullmatch(r'(?:collect|clean|extract|knowledge|inspect|targeted|merge|qgate)(?::[0-9]+)?', key),
                'invalid pre-report stage key', 'UNSAFE_PATH')
        require(key != 'report' and state['completed_stages'].get(key) == record,
                'snapshot stage was not committed in actual runtime')
        expected = f"artifacts/{rid}/{key.replace(':', '-')}.json"
        require(record['artifact_path'] == expected, 'stage path invalid', 'UNSAFE_PATH')
        env = snapshot.json(expected, digest(record['artifact_digest'], 'stage hash'))
        require(env['run_id'] == rid and env['request_id'] == key and env['error'] is None,
                'stage envelope identity invalid')
        pins[expected] = record['artifact_digest']
        for name, pin in env['files'].items():
            require(name.startswith(f'runs/{rid}/') and '/final/' not in name,
                    'snapshot output outside pre-report evidence', 'UNSAFE_PATH')
            snapshot.bytes(name, digest(pin, 'output hash'))
            require(name not in pins or pins[name] == pin, 'conflicting file pins')
            pins[name] = pin
        envelopes[key] = env
    require(payload['files'] == pins, 'snapshot files differ from committed envelope outputs')
    key = payload['stage_key']
    require(key.split(':')[0] in {'knowledge', 'merge'} and key in envelopes, 'no committed graph stage')
    graph = envelopes[key]['result']['graph']
    require(sha(json_text(graph).encode()) == payload['graph_sha256'], 'snapshot graph hash differs', 'HASH_MISMATCH')
    sources = {s['source_id']: s for s in graph['sources']}
    require(len(sources) == len(graph['sources']), 'duplicate source identity')
    paths = {}
    for source in payload['sources']:
        sid = source['source_id']
        require(sid in sources and sid not in paths, 'source binding identity differs')
        for name in ['clean_path', 'raw_path']:
            p = relative(source[name])
            require(p in pins, 'uncommitted evidence source')
            meta, body = source_body(snapshot.bytes(p, pins[p]), p)
            require(meta.get('evidence_kind', 'body') == 'body', 'snippet/discovery cannot support report')
            require(meta.get('source', meta.get('locator', '')) == source['locator'], 'source locator differs')
            if name == 'clean_path':
                require(body == sources[sid]['text'] and sha(body.encode()) == source['body_sha256']
                        == sources[sid]['content_sha256'], 'clean/source hash mismatch', 'HASH_MISMATCH')
        paths[sid] = source
    require(set(paths) == set(sources), 'snapshot omits source bodies')
    ids = set()
    for fact in graph['facts']:
        require(fact['claim_id'] not in ids, 'duplicate claim')
        ids.add(fact['claim_id'])
        require(fact['text'] in [c['text'] for c in fact['citations']], 'rewritten ledger fact')
        for citation in fact['citations']:
            _span(citation, sources)
    return snapshot, payload, graph, paths


def execute(args):
    try:
        snapshot, payload, graph, paths = read_snapshot(args.root, args.snapshot, args.snapshot_hash)
        scope = {'schema': 'evidence-query/v1', 'run_id': payload['run_id'],
                 'snapshot_sha256': args.snapshot_hash, 'source_count': len(graph['sources']),
                 'fact_count': len(graph['facts']), 'searched': payload['scope'],
                 'report_exists': f"runs/{payload['run_id']}/final/report.md" in snapshot.blobs,
                 'missing_supplements_searched': False}
        if args.view == 'graph':
            results = [{'graph': graph}]
            scope.update(matched_count=1, truncated=False)
        else:
            require(args.limit > 0 and args.offset >= 0, 'invalid query page', 'INVALID_ARGUMENT')
            results = []
            for source in graph['sources']:
                if args.source_id and source['source_id'] != args.source_id:
                    continue
                body = source['text']
                if args.text:
                    starts = [m.start() for m in re.finditer(re.escape(args.text), body)]
                    ranges = [((lambda p: p + 2 if p >= 0 else 0)(body.rfind('\n\n', 0, start)),
                               body.find('\n\n', start + len(args.text))) for start in starts]
                    ranges = [(a, len(body) if b < 0 else b) for a, b in ranges]
                else:
                    ranges = [(m.start(), m.end()) for m in re.finditer(r'\S[^\n]*(?:\n(?!\n)[^\n]+)*', body)]
                for a, b in dict.fromkeys(ranges):
                    if not body[a:b].strip():
                        continue
                    sid = source['source_id']
                    results.append({'source_id': sid, 'locator': source['locator'], 'title': source.get('title', ''),
                                    'content_sha256': source['content_sha256'], 'start_offset': a,
                                    'end_offset': b, 'text': body[a:b],
                                    'clean_path': str(Path(args.root).resolve() / paths[sid]['clean_path']),
                                    'raw_path': str(Path(args.root).resolve() / paths[sid]['raw_path']),
                                    'structure': 'table_or_paragraph', 'absence_proof': False})
            scope.update(matched_count=len(results), offset=args.offset,
                         truncated=args.offset + args.limit < len(results))
            results = results[args.offset:args.offset + args.limit]
        snapshot.unchanged()
        return {'status': 'success', 'authority': 'canonical', 'scope': scope, 'results': results}
    except (LayoutError, OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        return error_result('evidence', exc if isinstance(exc, LayoutError)
                            else LayoutError('evidence snapshot invalid: ' + str(exc)))
