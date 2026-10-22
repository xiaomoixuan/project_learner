"""Regression checks for unsafe audit acceptance, independent of prose quality."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/project-interview-dossier/scripts/check_audit.py'
SPEC = importlib.util.spec_from_file_location('audit_integrity', SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / 'input.md'
        self.draft = self.root / 'draft.md'
        self.input.write_text('课程项目，交付到分析建议。\n')
        self.draft.write_text('我交付分析建议；负责人尚未批准实施。\n')
        self.qpaths, self.lpaths, self.qdocs, self.ldocs = [], [], [], []
        for lens in 'ABC':
            q = {'id': lens + '-1', 'chain_id': lens + '-delivery', 'parent_id': None,
                 'question': '项目交付到哪一步？',
                 'basis': [{'source': 'input', 'source_id': None, 'locator': '项目描述', 'reason': '确认交付边界'}],
                 'scope': {'type': 'in_scope', 'reason': '本项目交付'},
                 'origin': {'type': 'blind_question', 'discovered_from': None}}
            qdoc = {'schema_version': '1.0', 'phase': 'question', 'case_id': 'fixture',
                    'lens': lens, 'auditor_id': 'instance-' + lens,
                    'input_sha256': AUDIT.sha(self.input.read_bytes()), 'draft_sha256': None,
                    'previous_questions': None, 'questions': [q]}
            qp, lp = self.root / (lens + '-questions.json'), self.root / (lens + '-ledger.json')
            qp.write_text(json.dumps(qdoc, ensure_ascii=False))
            ledger = {k: qdoc[k] for k in ['case_id', 'lens', 'auditor_id', 'input_sha256']}
            ledger.update(schema_version='1.0', phase='review', previous_ledger=None,
                          draft_sha256=AUDIT.body_sha(self.draft),
                          questions_sha256=AUDIT.sha(qp.read_bytes()),
                          answers=[dict(copy.deepcopy(q), answer='我已交付建议，未实施。', boundary='尚未批准实施。',
                                        evidence=[{'locator': '正文首段', 'content': '我交付分析建议；负责人尚未批准实施。'}],
                                        derivation={'premises': ['正文陈述交付边界'], 'steps': ['据正文识别交付阶段'], 'new_premises': []},
                                        repair={'locations': [], 'related_references': [], 'action': ''},
                                        recheck='首次逐问作答完成', history=[], status='通过', gap='')])
            self.qpaths.append(qp)
            self.lpaths.append(lp)
            self.qdocs.append(qdoc)
            self.ldocs.append(ledger)

    def run_check(self, allow_incomplete=False, single_auditor=False):
        for p, d in zip(self.lpaths, self.ldocs):
            p.write_text(json.dumps(d, ensure_ascii=False))
        return AUDIT.check(self.input, self.draft, self.qpaths, self.lpaths, allow_incomplete, single_auditor)

    def write_question(self, index=0):
        self.qpaths[index].write_text(json.dumps(self.qdocs[index], ensure_ascii=False))
        self.ldocs[index]['questions_sha256'] = AUDIT.sha(self.qpaths[index].read_bytes())

    def next_ledger(self, index=0):
        """Persist a real previous round and carry every row's complete history."""
        old_path, old = self.lpaths[index], copy.deepcopy(self.ldocs[index])
        old_path.write_text(json.dumps(old, ensure_ascii=False))
        self.lpaths[index] = old_path.with_name(old_path.stem + '-next.json')
        current = copy.deepcopy(old)
        current.update(phase='recheck', previous_ledger=old_path.name, handoff=None)
        for row, old_row in zip(current['answers'], old['answers']):
            row['history'].append({'draft_sha256': old['draft_sha256'], 'status': old_row['status'],
                                   'gap': old_row['gap'], 'ledger': old_path.name})
            row['recheck'] = '按本轮正文复答并核对引用'
        self.ldocs[index] = current
        return old_path

    def append_followup(self, authored_by=None):
        old_path = self.qpaths[0]
        self.qpaths[0] = old_path.with_name('A-questions-v2.json')
        self.qdocs[0]['previous_questions'] = old_path.name
        q = copy.deepcopy(self.qdocs[0]['questions'][0])
        q.update(id='A-2', parent_id='A-1', question='下一步由谁决定？',
                 origin={'type': 'review_followup', 'discovered_from': 'A-1'})
        if authored_by is not None:
            q['origin']['authored_by'] = authored_by
        self.qdocs[0]['questions'].append(q)
        answer = copy.deepcopy(self.ldocs[0]['answers'][0])
        answer.update(copy.deepcopy(q), history=[])
        self.ldocs[0]['answers'].append(answer)
        self.write_question()

    def test_complete_records_and_index_do_not_change_body_hash(self):
        self.assertEqual([], self.run_check()['errors'])
        with self.draft.open('a') as f:
            f.write('<!-- INTERVIEW_AUDIT_INDEX -->\n本次问题索引\n')
        self.assertEqual([], self.run_check()['errors'])

    def test_one_unresolved_question_cannot_hide_in_other_passes(self):
        self.ldocs[1]['answers'][0].update(status='缺失', gap='没有实施批准材料。')
        self.assertTrue(self.run_check()['errors'])
        self.assertEqual([], self.run_check(allow_incomplete=True)['errors'])

    def test_missing_subquestion_is_rejected(self):
        self.ldocs[0]['answers'] = []
        self.assertTrue(self.run_check()['errors'])

    def test_changed_body_invalidates_old_pass(self):
        self.draft.write_text('我已实施改版。\n')
        self.assertTrue(self.run_check()['errors'])

    def test_reused_author_identity_is_rejected(self):
        self.ldocs[1]['auditor_id'] = self.ldocs[0]['auditor_id']
        self.assertTrue(self.run_check()['errors'])

    def test_question_cannot_be_weakened_in_answer(self):
        self.ldocs[0]['answers'][0]['question'] = '什么是项目？'
        self.assertTrue(self.run_check()['errors'])

    def test_frozen_question_file_cannot_change_silently(self):
        q = copy.deepcopy(self.qdocs[0])
        q['questions'][0]['question'] = '什么是项目？'
        self.qpaths[0].write_text(json.dumps(q))
        self.assertTrue(self.run_check()['errors'])

    def test_new_critical_premise_or_empty_evidence_cannot_pass(self):
        self.ldocs[0]['answers'][0]['derivation']['new_premises'] = ['负责人已经批准实施']
        self.assertTrue(self.run_check()['errors'])
        self.ldocs[0]['answers'][0]['derivation']['new_premises'] = []
        self.ldocs[0]['answers'][0]['evidence'] = []
        self.assertTrue(self.run_check()['errors'])

    def test_new_question_version_cannot_drop_old_obligation(self):
        old = copy.deepcopy(self.qdocs[0])
        old['questions'].append(dict(old['questions'][0], id='A-2', question='为什么尚未实施？'))
        (self.root / 'A-questions-old.json').write_text(json.dumps(old, ensure_ascii=False))
        self.qdocs[0]['previous_questions'] = 'A-questions-old.json'
        self.qpaths[0].write_text(json.dumps(self.qdocs[0], ensure_ascii=False))
        self.ldocs[0]['questions_sha256'] = AUDIT.sha(self.qpaths[0].read_bytes())
        self.assertTrue(self.run_check()['errors'])

    def test_cross_lens_duplicate_id_is_rejected(self):
        self.qdocs[1]['questions'][0]['id'] = 'A-1'
        self.ldocs[1]['answers'][0]['id'] = 'A-1'
        self.qpaths[1].write_text(json.dumps(self.qdocs[1], ensure_ascii=False))
        self.ldocs[1]['questions_sha256'] = AUDIT.sha(self.qpaths[1].read_bytes())
        self.assertTrue(self.run_check()['errors'])

    def test_missing_contract_fields_are_rejected(self):
        original = copy.deepcopy(self.ldocs[0]['answers'][0])
        for key in original:
            with self.subTest(field=key):
                row = copy.deepcopy(original)
                del row[key]
                self.ldocs[0]['answers'][0] = row
                self.assertTrue(self.run_check()['errors'])

    def test_missing_question_metadata_and_nested_fields_are_rejected(self):
        original = copy.deepcopy(self.qdocs[0])
        for container, key in [('question', 'chain_id'), ('basis', 'locator'),
                               ('scope', 'reason'), ('origin', 'discovered_from')]:
            with self.subTest(container=container, field=key):
                self.qdocs[0] = copy.deepcopy(original)
                row = self.qdocs[0]['questions'][0]
                target = row if container == 'question' else row[container][0] if container == 'basis' else row[container]
                del target[key]
                self.ldocs[0]['answers'][0].update(copy.deepcopy(row))
                self.write_question()
                self.assertTrue(self.run_check()['errors'])

    def test_frozen_scope_and_source_cannot_change_in_answer(self):
        original = copy.deepcopy(self.ldocs[0]['answers'][0])
        changes = {'scope': {'type': 'boundary', 'reason': '改为范围外'},
                   'basis': [{'source': 'input', 'source_id': None, 'locator': '别处', 'reason': '别的依据'}],
                   'origin': {'type': 'blind_question', 'discovered_from': None, 'authored_by': 'other'}}
        for key, value in changes.items():
            with self.subTest(field=key):
                self.ldocs[0]['answers'][0] = dict(copy.deepcopy(original), **{key: value})
                self.assertTrue(self.run_check()['errors'])

    def test_legal_recheck_preserves_prior_state(self):
        self.next_ledger()
        self.assertEqual([], self.run_check()['errors'])

    def test_missing_previous_ledger_and_cycles_are_rejected(self):
        old_path = self.next_ledger()
        self.ldocs[0]['previous_ledger'] = 'missing-ledger.json'
        self.assertTrue(self.run_check()['errors'])
        self.ldocs[0]['previous_ledger'] = self.lpaths[0].name
        self.assertTrue(self.run_check()['errors'])
        self.ldocs[0]['previous_ledger'] = old_path.name
        self.assertEqual([], self.run_check()['errors'])

    def test_history_must_copy_previous_status_hash_gap_and_path(self):
        self.next_ledger()
        original = copy.deepcopy(self.ldocs[0]['answers'][0]['history'][0])
        changes = {'status': '缺失', 'draft_sha256': '0' * 64, 'gap': '被改写的断点',
                   'ledger': 'another-ledger.json'}
        for key, value in changes.items():
            with self.subTest(field=key):
                self.ldocs[0]['answers'][0]['history'] = [dict(original, **{key: value})]
                self.assertTrue(self.run_check()['errors'])

    def test_multiround_history_cannot_be_erased(self):
        self.next_ledger()
        self.next_ledger()
        self.assertEqual([], self.run_check()['errors'])
        self.ldocs[0]['answers'][0]['history'].pop(0)
        self.assertTrue(self.run_check()['errors'])

    def test_previous_ledger_cannot_change_case_lens_owner_or_input(self):
        old_path = self.next_ledger()
        original = json.loads(old_path.read_text())
        for key in ['case_id', 'lens', 'auditor_id', 'input_sha256']:
            with self.subTest(field=key):
                changed = dict(original, **{key: '0' * 64 if key == 'input_sha256' else 'different'})
                old_path.write_text(json.dumps(changed))
                self.assertTrue(self.run_check()['errors'])

    def test_previous_question_version_must_be_retained(self):
        self.next_ledger()
        self.append_followup()
        self.assertEqual([], self.run_check()['errors'])
        self.qdocs[0]['previous_questions'] = None
        self.write_question()
        self.assertTrue(self.run_check()['errors'])

    def test_old_question_cannot_disappear_even_with_a_matching_current_ledger(self):
        self.next_ledger()
        self.append_followup()
        self.qdocs[0]['questions'] = self.qdocs[0]['questions'][1:]
        self.ldocs[0]['answers'] = self.ldocs[0]['answers'][1:]
        self.write_question()
        self.assertTrue(self.run_check()['errors'])

    def test_failure_to_pass_requires_repair_action_and_recheck(self):
        self.ldocs[0]['answers'][0].update(status='缺失', gap='缺少决定依据')
        self.next_ledger()
        row = self.ldocs[0]['answers'][0]
        row.update(status='通过', gap='')
        self.assertTrue(self.run_check()['errors'])
        row['repair'].update(locations=['正文首段'], action='补齐决定依据')
        self.assertEqual([], self.run_check()['errors'])
        row['recheck'] = ''
        self.assertTrue(self.run_check()['errors'])

    def test_legal_handoff_keeps_frozen_owner_and_new_reviewer(self):
        self.next_ledger()
        self.ldocs[0].update(reviewer_id='replacement-A',
                             handoff={'from_reviewer_id': 'instance-A', 'to_reviewer_id': 'replacement-A',
                                      'reason': '原实例丢失，接手完整历史'})
        self.assertEqual([], self.run_check()['errors'])
        self.next_ledger()
        self.assertEqual([], self.run_check()['errors'])

    def test_first_review_can_be_handed_off_before_any_ledger(self):
        self.ldocs[0].update(reviewer_id='replacement-A',
                             handoff={'from_reviewer_id': 'instance-A', 'to_reviewer_id': 'replacement-A',
                                      'reason': '原实例完成出题后丢失'})
        self.assertEqual([], self.run_check()['errors'])

    def test_reviewer_change_requires_a_valid_handoff(self):
        self.next_ledger()
        self.ldocs[0]['reviewer_id'] = 'replacement-A'
        self.assertTrue(self.run_check()['errors'])
        valid = {'from_reviewer_id': 'instance-A', 'to_reviewer_id': 'replacement-A', 'reason': '原实例丢失'}
        for key, value in [('from_reviewer_id', 'not-the-predecessor'),
                           ('to_reviewer_id', 'not-the-reviewer'), ('reason', '')]:
            with self.subTest(field=key):
                self.ldocs[0]['handoff'] = dict(valid, **{key: value})
                self.assertTrue(self.run_check()['errors'])

    def test_second_handoff_connects_actual_predecessor(self):
        self.ldocs[0].update(reviewer_id='replacement-A',
                             handoff={'from_reviewer_id': 'instance-A', 'to_reviewer_id': 'replacement-A',
                                      'reason': '原实例丢失'})
        self.next_ledger()
        self.ldocs[0].update(reviewer_id='replacement-A2',
                             handoff={'from_reviewer_id': 'replacement-A', 'to_reviewer_id': 'replacement-A2',
                                      'reason': '前任实例丢失'})
        self.assertEqual([], self.run_check()['errors'])
        self.ldocs[0]['handoff']['from_reviewer_id'] = 'instance-A'
        self.assertTrue(self.run_check()['errors'])

    def test_actual_reviewers_must_remain_distinct(self):
        self.ldocs[0].update(reviewer_id='instance-B',
                             handoff={'from_reviewer_id': 'instance-A', 'to_reviewer_id': 'instance-B',
                                      'reason': '接替'})
        self.assertTrue(self.run_check()['errors'])

    def test_replacement_followup_records_real_author(self):
        self.next_ledger()
        self.ldocs[0].update(reviewer_id='replacement-A',
                             handoff={'from_reviewer_id': 'instance-A', 'to_reviewer_id': 'replacement-A',
                                      'reason': '原实例丢失'})
        self.append_followup(authored_by='replacement-A')
        self.assertEqual([], self.run_check()['errors'])
        del self.qdocs[0]['questions'][1]['origin']['authored_by']
        del self.ldocs[0]['answers'][1]['origin']['authored_by']
        self.write_question()
        self.assertTrue(self.run_check()['errors'])

    def test_history_paths_are_relative_to_each_containing_ledger(self):
        self.next_ledger()
        nested = self.root / 'next-round'
        nested.mkdir()
        self.lpaths[0] = nested / self.lpaths[0].name
        self.ldocs[0]['previous_ledger'] = '../A-ledger.json'
        self.ldocs[0]['answers'][0]['history'][0]['ledger'] = '../A-ledger.json'
        self.assertEqual([], self.run_check()['errors'])

    def test_optional_identity_fields_keep_legacy_defaults(self):
        self.ldocs[0].update(reviewer_id=None, handoff=None)
        self.assertEqual([], self.run_check()['errors'])


    def single_fixture(self):
        self.qpaths, self.lpaths = self.qpaths[:1], self.lpaths[:1]
        self.qdocs, self.ldocs = self.qdocs[:1], self.ldocs[:1]
        self.qdocs[0].update(lens='S', auditor_id='instance-S')
        self.ldocs[0].update(lens='S', auditor_id='instance-S')
        self.qdocs[0]['questions'][0].update(id='S-1', chain_id='S-delivery')
        self.ldocs[0]['answers'][0].update(copy.deepcopy(self.qdocs[0]['questions'][0]))
        self.write_question()

    def test_single_mode_requires_explicit_opt_in(self):
        self.single_fixture()
        self.assertTrue(self.run_check()['errors'])
        self.assertEqual([], self.run_check(single_auditor=True)['errors'])

    def test_single_mode_does_not_accept_disguised_three_lenses(self):
        self.assertTrue(self.run_check(single_auditor=True)['errors'])
        self.assertEqual([], self.run_check()['errors'])

    def test_single_mode_retains_failure_and_hash_guards(self):
        self.single_fixture()
        self.ldocs[0]['answers'][0].update(status='缺失', gap='缺关键解释')
        self.assertTrue(self.run_check(single_auditor=True)['errors'])
        self.assertEqual([], self.run_check(allow_incomplete=True, single_auditor=True)['errors'])
        self.draft.write_text('正文已变化')
        self.assertTrue(self.run_check(allow_incomplete=True, single_auditor=True)['errors'])

    def test_single_mode_cli_checks_real_records(self):
        import subprocess
        import sys
        self.single_fixture()
        self.run_check(single_auditor=True)
        args = [sys.executable, str(SCRIPT), '--input', str(self.input), '--draft', str(self.draft),
                '--questions', str(self.qpaths[0]), '--ledgers', str(self.lpaths[0])]
        rejected = subprocess.run(args, capture_output=True, text=True)
        self.assertNotEqual(0, rejected.returncode)
        accepted = subprocess.run(args + ['--single-auditor'], capture_output=True, text=True)
        self.assertEqual(0, accepted.returncode, accepted.stdout + accepted.stderr)
        self.assertEqual([], json.loads(accepted.stdout)['errors'])


if __name__ == '__main__':
    unittest.main()
