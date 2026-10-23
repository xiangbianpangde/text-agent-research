"""Direct full-source query contract checks, independent of LLM behavior."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from researchctl.layouts.evidence_snapshot import execute


class ByteSnapshot:
    blobs = {}
    def unchanged(self):
        return None


def query(body, **values):
    graph = {'sources': [{'source_id': 's', 'text': body, 'locator': 'https://fixture.invalid',
                          'content_sha256': 'a' * 64, 'title': 'Source'}], 'facts': []}
    binding = {'s': {'clean_path': 'clean/source.md', 'raw_path': 'raw/source.md'}}
    args = SimpleNamespace(root='/root', snapshot='evidence', snapshot_hash='b' * 64,
                           view='body', source_id=None, text=None, offset=0, limit=50)
    for name, value in values.items():
        setattr(args, name, value)
    with patch('researchctl.layouts.evidence_snapshot.read_snapshot',
               return_value=(ByteSnapshot(), {'run_id': '1' * 32, 'scope': 'clean_body'}, graph, binding)):
        return execute(args)


def test_first_paragraph_offset_is_not_shifted_by_missing_separator():
    response = query('Methods adjusted for age.\n\nResults.', text='Methods')
    assert response['status'] == 'success'
    assert response['results'][0]['start_offset'] == 0
    assert response['results'][0]['text'] == 'Methods adjusted for age.'


def test_full_body_paging_preserves_table_headers_and_is_not_absence_proof():
    text = 'Intro.\n\nTable 4 | Adjusted OR\nPPH | 5.43\nFootnote: per delivery.\n\nEnd.'
    response = query(text, offset=1, limit=1)
    assert response['status'] == 'success' and response['scope']['truncated'] is True
    assert 'Table 4' in response['results'][0]['text']
    assert 'Footnote:' in response['results'][0]['text']
    assert response['results'][0]['absence_proof'] is False


def test_historical_report_does_not_mark_current_snapshot_as_reported():
    with patch.object(ByteSnapshot, 'blobs', {'runs/' + '2' * 32 + '/final/report.md': b'old'}):
        response = query('Current evidence.')
    assert response['scope']['report_exists'] is False


def test_unmatched_text_is_only_scoped_empty_lookup_not_source_absence():
    response = query('Methods existed.', text='impossible')
    assert response['results'] == []
    assert response['scope']['missing_supplements_searched'] is False
