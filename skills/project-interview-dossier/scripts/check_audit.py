#!/usr/bin/env python3
"""Check audit record integrity. Does not judge answer quality or agent independence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

MARKER = b'<!-- INTERVIEW_AUDIT_INDEX -->'
STATUSES = {'通过', '过浅', '缺失', '冲突'}
QUESTION_FIELDS = ('id', 'chain_id', 'parent_id', 'question', 'basis', 'scope', 'origin')
IDENTITY_FIELDS = ('case_id', 'lens', 'auditor_id', 'input_sha256')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def body_sha(path):
    return sha(path.read_bytes().split(MARKER, 1)[0])


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def nullable_text(value):
    return value is None or nonempty(value)


def text_list(value):
    return isinstance(value, list) and all(nonempty(item) for item in value)


def fields(record, rules, prefix, errors):
    """Validate structure only; descriptions and answers are never interpreted."""
    if not isinstance(record, dict):
        errors.append(f'{prefix}: expected object')
        return False
    valid = True
    for key, rule in rules.items():
        if key not in record or not rule(record[key]):
            errors.append(f'{prefix}: missing/invalid {key}')
            valid = False
    return valid


def record_chain(path, document, link, errors):
    """Return oldest first, resolving each link relative to its containing file."""
    chain, seen = [], set()
    while True:
        path = path.resolve()
        if path in seen:
            errors.append(f'{link}: history contains a cycle at {path.name}')
            break
        seen.add(path)
        if not isinstance(document, dict):
            errors.append(f'{path.name}: expected object')
            break
        chain.append((path, document))
        reference = document.get(link)
        if reference is None:
            break
        if not nonempty(reference):
            errors.append(f'{path.name}: invalid {link}')
            break
        path = path.parent / reference
        try:
            document = read(path)
        except (OSError, ValueError) as exc:
            errors.append(f'{link}: cannot read {path}: {exc}')
            break
    return list(reversed(chain))


def question_fields(row, prefix, errors):
    if not fields(row, {
        'id': nonempty, 'chain_id': nonempty, 'parent_id': nullable_text,
        'question': nonempty, 'basis': lambda v: isinstance(v, list) and bool(v),
        'scope': lambda v: isinstance(v, dict), 'origin': lambda v: isinstance(v, dict),
    }, prefix, errors):
        return
    for basis in row['basis']:
        fields(basis, {'source': nonempty, 'source_id': nullable_text,
                       'locator': nonempty, 'reason': nonempty}, f'{prefix}/basis', errors)
    fields(row['scope'], {'type': lambda v: v in ('in_scope', 'boundary'),
                          'reason': nonempty}, f'{prefix}/scope', errors)
    origin = row['origin']
    if fields(origin, {'type': lambda v: v in ('blind_question', 'review_followup'),
                       'discovered_from': nullable_text}, f'{prefix}/origin', errors):
        if (origin['type'] == 'blind_question') != (origin['discovered_from'] is None):
            errors.append(f'{prefix}: origin/discovered_from mismatch')
    if 'authored_by' in origin and not nullable_text(origin['authored_by']):
        errors.append(f'{prefix}: invalid origin.authored_by')


def row_map(document, field, prefix, errors):
    rows = document.get(field)
    if not isinstance(rows, list) or not rows:
        errors.append(f'{prefix}: empty/invalid {field}')
        return {}
    result = {}
    for row in rows:
        question_fields(row, prefix, errors)
        if not isinstance(row, dict) or not nonempty(row.get('id')):
            continue
        rid = row['id']
        if rid in result:
            errors.append(f'{prefix}: duplicate ID {rid}')
        result[rid] = row
    for rid, row in result.items():
        parent = row.get('parent_id')
        if parent is not None and (not isinstance(parent, str) or parent not in result or parent == rid):
            errors.append(f'{prefix}/{rid}: unknown/self parent ID')
        origin = row.get('origin')
        if isinstance(origin, dict) and origin.get('type') == 'review_followup':
            source = origin.get('discovered_from')
            if not isinstance(source, str) or source not in result or source == rid:
                errors.append(f'{prefix}/{rid}: unknown/self followup source ID')
    return result


def common_fields(document, prefix, errors):
    fields(document, {'schema_version': lambda v: v == '1.0',
                      'case_id': nonempty, 'lens': nonempty, 'auditor_id': nonempty,
                      'input_sha256': digest}, prefix, errors)


def question_versions(path, document, errors):
    versions, previous_rows = {}, {}
    chain = record_chain(path, document, 'previous_questions', errors)
    for index, (qpath, qdoc) in enumerate(chain):
        prefix = qpath.name
        common_fields(qdoc, prefix, errors)
        fields(qdoc, {'phase': lambda v: v == 'question', 'draft_sha256': lambda v: v is None,
                      'previous_questions': nullable_text}, prefix, errors)
        for key in IDENTITY_FIELDS:
            if qdoc.get(key) != document.get(key):
                errors.append(f'{prefix}: question history changes {key}')
        rows = row_map(qdoc, 'questions', prefix, errors)
        for rid, old in previous_rows.items():
            if rows.get(rid) != old:
                errors.append(f'{prefix}: frozen obligation deleted or modified: {rid}')
        for rid, row in rows.items():
            origin = row.get('origin', {})
            if not isinstance(origin, dict):
                continue
            if index == 0 and origin.get('type') == 'review_followup':
                errors.append(f'{prefix}/{rid}: followup lacks frozen question history')
            if origin.get('type') == 'blind_question' and origin.get('authored_by') not in (None, qdoc.get('auditor_id')):
                errors.append(f'{prefix}/{rid}: blind question author differs from owner')
        versions[sha(qpath.read_bytes())] = (index, rows)
        previous_rows = rows
    return versions


def answer_fields(row, prefix, errors):
    if not fields(row, {
        'answer': nonempty, 'boundary': nonempty,
        'status': lambda v: isinstance(v, str) and v in STATUSES,
        'gap': lambda v: isinstance(v, str), 'evidence': lambda v: isinstance(v, list),
        'derivation': lambda v: isinstance(v, dict), 'repair': lambda v: isinstance(v, dict),
        'recheck': nonempty, 'history': lambda v: isinstance(v, list),
    }, prefix, errors):
        return
    for entry in row['evidence']:
        fields(entry, {'locator': nonempty, 'content': nonempty}, f'{prefix}/evidence', errors)
    fields(row['derivation'], {'premises': text_list, 'steps': text_list,
                               'new_premises': text_list}, f'{prefix}/derivation', errors)
    fields(row['repair'], {'locations': text_list, 'related_references': text_list,
                           'action': lambda v: isinstance(v, str)}, f'{prefix}/repair', errors)
    for entry in row['history']:
        fields(entry, {'draft_sha256': digest, 'status': lambda v: isinstance(v, str) and v in STATUSES,
                       'gap': lambda v: isinstance(v, str), 'ledger': nonempty}, f'{prefix}/history', errors)
    if row['status'] == '通过':
        if not row['evidence']:
            errors.append(f'{prefix}: pass lacks concrete evidence')
        if row['derivation'].get('new_premises'):
            errors.append(f'{prefix}: pass depends on new premises')
        if row['gap'] != '':
            errors.append(f'{prefix}: pass retains a gap')
    elif not nonempty(row['gap']):
        errors.append(f'{prefix}: non-pass lacks gap')


def reviewer(document):
    return document.get('reviewer_id') or document.get('auditor_id')


def history_values(row, path):
    """Canonicalize references so a later ledger may live in another directory."""
    entries = row.get('history')
    if not isinstance(entries, list):
        return None
    values = []
    for entry in entries:
        if not isinstance(entry, dict) or not nonempty(entry.get('ledger')):
            return None
        values.append((entry.get('draft_sha256'), entry.get('status'), entry.get('gap'),
                       (path.parent / entry['ledger']).resolve()))
    return values


def check_ledgers(path, document, versions, errors):
    previous, previous_path, previous_rows, previous_version = None, None, {}, -1
    chain = record_chain(path, document, 'previous_ledger', errors)
    for lpath, ledger in chain:
        prefix = lpath.name
        common_fields(ledger, prefix, errors)
        fields(ledger, {'phase': lambda v: v in ('review', 'recheck'), 'draft_sha256': digest,
                        'questions_sha256': digest, 'previous_ledger': nullable_text}, prefix, errors)
        for key in IDENTITY_FIELDS:
            if ledger.get(key) != document.get(key):
                errors.append(f'{prefix}: ledger history changes {key}')
        if (ledger.get('phase') == 'recheck') != (ledger.get('previous_ledger') is not None):
            errors.append(f'{prefix}: phase/previous_ledger mismatch')
        if 'reviewer_id' in ledger and not nullable_text(ledger['reviewer_id']):
            errors.append(f'{prefix}: invalid reviewer_id')
        current_reviewer = reviewer(ledger)
        prior_reviewer = reviewer(previous) if previous else ledger.get('auditor_id')
        handoff = ledger.get('handoff')
        if handoff is not None:
            if fields(handoff, {'from_reviewer_id': nonempty, 'to_reviewer_id': nonempty,
                                'reason': nonempty}, f'{prefix}/handoff', errors):
                if handoff['from_reviewer_id'] != prior_reviewer or handoff['to_reviewer_id'] != current_reviewer:
                    errors.append(f'{prefix}: handoff does not connect actual reviewers')
                if current_reviewer == prior_reviewer:
                    errors.append(f'{prefix}: handoff does not change reviewer')
        elif current_reviewer != prior_reviewer:
            errors.append(f'{prefix}: reviewer change lacks handoff')
        rows = row_map(ledger, 'answers', prefix, errors)
        question_hash = ledger.get('questions_sha256')
        version = versions.get(question_hash) if isinstance(question_hash, str) else None
        if version is None:
            errors.append(f'{prefix}: ledger question version missing from frozen history')
        else:
            index, questions = version
            if index < previous_version:
                errors.append(f'{prefix}: ledger rolls back question version')
            previous_version = index
            if set(rows) != set(questions):
                errors.append(f'{prefix}: missing/extra answer IDs {sorted(set(rows) ^ set(questions))}')
            for rid in rows.keys() & questions.keys():
                for key in QUESTION_FIELDS:
                    if key not in rows[rid] or rows[rid][key] != questions[rid].get(key):
                        errors.append(f'{prefix}/{rid}: frozen {key} changed or missing')
                origin = questions[rid].get('origin', {})
                if rid not in previous_rows and isinstance(origin, dict) and origin.get('type') == 'review_followup':
                    if (origin.get('authored_by') or ledger.get('auditor_id')) != current_reviewer:
                        errors.append(f'{prefix}/{rid}: new followup author differs from actual reviewer')
        for rid in previous_rows.keys() - rows.keys():
            errors.append(f'{prefix}: previous answer obligation deleted: {rid}')
        for rid, row in rows.items():
            key = f'{prefix}/{rid}'
            answer_fields(row, key, errors)
            expected_history = []
            if rid in previous_rows:
                old = previous_rows[rid]
                inherited = history_values(old, previous_path)
                if inherited is not None:
                    expected_history = inherited + [(previous.get('draft_sha256'), old.get('status'),
                                                     old.get('gap'), previous_path)]
                else:
                    expected_history = None
                if isinstance(old.get('status'), str) and old['status'] in STATUSES - {'通过'} and row.get('status') == '通过':
                    repair = row.get('repair')
                    if not isinstance(repair, dict) or not nonempty(repair.get('action')) or not nonempty(row.get('recheck')):
                        errors.append(f'{key}: repaired pass lacks repair action/recheck')
            if history_values(row, lpath) != expected_history:
                errors.append(f'{key}: history does not preserve prior ledger states')
        previous, previous_path, previous_rows = ledger, lpath, rows
    return previous_rows


def check(input_path, draft_path, question_paths, ledger_paths, allow_incomplete=False):
    errors, counts = [], Counter()
    input_hash, draft_hash = sha(input_path.read_bytes()), body_sha(draft_path)
    questions, ledgers = {}, {}
    for paths, target, label in [(question_paths, questions, 'questions'), (ledger_paths, ledgers, 'ledger')]:
        for path in paths:
            item = read(path)
            if not isinstance(item, dict):
                errors.append(f'{label}: expected object in {path.name}')
                continue
            lens = item.get('lens')
            if not nonempty(lens) or lens in target:
                errors.append(f'{label}: missing/duplicate lens {lens!r}')
                continue
            target[lens] = (path, item)
    if not {'A', 'B', 'C'} <= set(questions):
        errors.append('Missing required question lenses A/B/C')
    if set(questions) != set(ledgers):
        errors.append('Question and ledger lenses differ')
    identities, reviewers, cases, all_question_ids = [], [], set(), []
    for lens, (qpath, qdoc) in questions.items():
        if lens not in ledgers:
            continue
        lpath, ledger = ledgers[lens]
        prefix = f'{lens}/{lpath.name}'
        local_errors = []
        versions = question_versions(qpath, qdoc, local_errors)
        arows = check_ledgers(lpath, ledger, versions, local_errors)
        errors.extend(f'{prefix}: {error}' for error in local_errors)
        identities.append(str(ledger.get('auditor_id')))
        reviewers.append(str(reviewer(ledger)))
        cases.add(str(ledger.get('case_id')))
        for key in ['case_id', 'lens', 'auditor_id']:
            if not nonempty(qdoc.get(key)) or qdoc.get(key) != ledger.get(key):
                errors.append(f'{prefix}: invalid/mismatched {key}')
        if qdoc.get('input_sha256') != input_hash or ledger.get('input_sha256') != input_hash:
            errors.append(f'{prefix}: input hash mismatch')
        if ledger.get('draft_sha256') != draft_hash:
            errors.append(f'{prefix}: body hash mismatch')
        if ledger.get('questions_sha256') != sha(qpath.read_bytes()):
            errors.append(f'{prefix}: frozen questions hash mismatch')
        latest_rows = versions.get(sha(qpath.read_bytes()), (None, {}))[1]
        all_question_ids.extend(latest_rows)
        for rid, row in arows.items():
            key = f'{prefix}/{rid}'
            status = row.get('status')
            counts[str(status)] += 1
            if status != '通过' and not allow_incomplete:
                errors.append(f'{key}: unresolved {status}')
    if len(identities) != len(set(identities)):
        errors.append('Auditor identities are not distinct across lenses')
    if len(reviewers) != len(set(reviewers)):
        errors.append('Actual reviewer identities are not distinct across lenses')
    if len(all_question_ids) != len(set(all_question_ids)):
        errors.append('Question IDs are not unique across lenses')
    if len(cases) != 1:
        errors.append('Records do not identify one consistent case')
    return {'body_sha256': draft_hash, 'status_counts': dict(counts), 'errors': errors,
            'gate_mode': 'interim' if allow_incomplete else 'final',
            'all_recorded_statuses_pass': bool(counts) and set(counts) == {'通过'},
            'meaning': 'Record integrity only; content and independence require actual review.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--draft', type=Path, required=True)
    parser.add_argument('--questions', type=Path, nargs='+', required=True)
    parser.add_argument('--ledgers', type=Path, nargs='+', required=True)
    parser.add_argument('--allow-incomplete', action='store_true', help='Check interim records without requiring all answers to pass')
    args = parser.parse_args()
    try:
        result = check(args.input, args.draft, args.questions, args.ledgers, args.allow_incomplete)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result = {'errors': [f'Invalid record: {exc}']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['errors']))
