"""Offline permission tests; synthetic observations are not research evidence.

Set P3_ABLATION_CONFIG_DIR to the research repository's configs/research directory.
No Host, Store, Main or Reporter agent is created.
"""
import builtins
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from jsonschema import Draft202012Validator
from tools.research import analysis, config, experience, passive_search, reporter, search, structure_intent, structure_research
from tools.research.agent import plan_schema, selected_analysis_schema
from tools.research.contracts import AnalysisRequest, FamilyMixedSearch
from tools.research.scientific_intent import question_schema, scientific_actions


REF = dict(artifact_id='0' * 64, media_type='application/json')
original_import = builtins.__import__


def no_mujoco(name, *args, **kwargs):
    if name == 'mujoco' or name.startswith('mujoco.'):
        raise AssertionError('No MuJoCo in offline tests')
    return original_import(name, *args, **kwargs)


def setUpModule():
    global offline_patches
    offline_patches = ExitStack()
    for target, value in [('subprocess.Popen', AssertionError('No Worker')),
                          ('socket.socket.connect', AssertionError('No network'))]:
        offline_patches.enter_context(patch(target, side_effect=value))
    offline_patches.enter_context(patch('builtins.__import__', side_effect=no_mujoco))
    offline_patches.enter_context(patch('platform.machine', return_value='AMD64'))


def tearDownModule():
    offline_patches.close()


class PreparationReached(Exception):
    pass


class P3AblationGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get('P3_ABLATION_CONFIG_DIR'):
            raise unittest.SkipTest('Set P3_ABLATION_CONFIG_DIR to existing research sources')
        cls.directory = Path(os.environ['P3_ABLATION_CONFIG_DIR']).resolve()
        cls.source = cls.directory / 'study_p3_passive_progressive_stiffness_autonomous_v1_2.json'
        cls.original_sha = hashlib.sha256(cls.source.read_bytes()).digest()
        cls.full = config.resolve(cls.source)
        cls.historical_manifest = json.loads((cls.directory.parents[1] / 'docs/research/p3-autonomous-study-v1_2-launch-20261110/knowledge-manifest.json').read_text(encoding='utf-8'))
        cls.groups = {name: config.resolve(cls.directory / ('study_p3_ablation_' + name + '_v1.json'))
                      for name in ('no_math', 'no_knowledge', 'no_interact')}

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(cls.source.read_bytes()).digest() == cls.original_sha

    def query(self, spec):
        return FamilyMixedSearch(version='family_mixed_search_v1',
            family_space_identity=spec['family_space_identity'], variable_groups=['lengths'],
            segment_counts=[4], tendon_counts=[4], screening_fidelity='screening',
            objective='task_violation', operating_point='standardized_initial_pretension',
            evaluation_mode='passive_task_response', max_proposals=24, max_evaluations=16)

    def request(self, spec, operation):
        return AnalysisRequest.model_validate(dict(candidate=REF, operation='mechanism_structure_v1',
            model_source='mujoco', operating_point='standardized_initial_pretension', protocol=spec['analysis_protocol'],
            mechanism_study=dict(operation=operation, target=dict(quantity='total_mass', goal='decrease'),
                point_semantics='re_equilibrated', max_evaluations=4,
                parameter_paths=['segments.0.length_m', 'segments.0.young_pa'] if operation == 'interact' else [])))

    def dispatch(self, spec, operation):
        host = SimpleNamespace(store=Mock(), run_id='offline-fixture')
        host.store.lookup.return_value = None
        with patch.object(analysis, 'state', return_value=dict(spec=spec)), \
                patch('tools.research.research_context.mathematics_authorization',
                      return_value=dict(registered_study_scope_authorized=True)), \
                patch.object(analysis, 'verify_candidate', side_effect=PreparationReached) as prepare, \
                patch.object(analysis, 'calculate', side_effect=AssertionError('No calculation')):
            value = analysis.dispatch(host, self.request(spec, operation), 'offline', guard=Mock())
            prepare.assert_not_called()
            return value

    def test_configs_preserve_frozen_task_physics_space_and_identities(self):
        ids = set(); destinations = set()
        for name, spec in self.groups.items():
            ids.add(spec['study_id']); destinations.add(spec['evidence_destination'])
            for field in ('canonical_task', 'family_space', 'family_execution', 'candidate_initialization',
                          'initial_structure_strategy', 'runtime', 'scoring_window_s', 'fidelity_policy'):
                if field in self.full:
                    self.assertEqual(spec[field], self.full[field], field)
            for field in ('robot', 'task', 'discretization'):
                if field in self.full['configuration']:
                    self.assertEqual(spec['configuration'][field], self.full['configuration'][field], field)
            for field in ('backend', 'dynamics_model', 'discretization'):
                self.assertEqual(spec['configuration']['policy'][field], self.full['configuration']['policy'][field])
            self.assertEqual(spec['initial_structure_strategy'], 'agent_choice')
            self.assertNotIn('fixed_structure_reference', spec)
            self.assertEqual(spec['configuration']['task']['timing']['duration_s'], 20)
            self.assertEqual(len(spec['configuration']['task']['goal']['data']['load_conditions']), 2)
            for value in ('candidate_2915', 'historical_control'):
                self.assertNotIn(value, (self.directory / ('study_p3_ablation_' + name + '_v1.json')).read_text())
        self.assertEqual(len(ids), 3); self.assertEqual(len(destinations), 3)

    def test_finite_count_budgets_and_search_contract(self):
        for name, spec in self.groups.items():
            for key in ('provider_requests', 'protected_provider_requests', 'physical_launches',
                        'public_operations', 'local_solves', 'offline_nlp', 'bdf_replays', 'mathematical_evaluations'):
                self.assertIs(type(spec['budgets'][key]), int)
            self.assertEqual(spec['budgets']['provider_requests'], 200)
            self.assertEqual(spec['budgets']['protected_provider_requests'], 4)
            self.assertEqual(spec['budgets']['public_operations'], 800)
            self.assertEqual(spec['configuration']['policy']['budget']['model_calls'], 200)
            self.assertEqual(spec['configuration']['policy']['budget']['tool_calls'], 800)
            self.assertEqual(spec['configuration']['policy']['budget']['backend_solves'], 150)
            self.assertEqual(spec['budgets']['physical_launches'], 150)
            self.assertEqual(spec['budgets']['mathematical_evaluations'], 0 if name == 'no_math' else 100)
            self.assertEqual(spec['family_search']['max_proposals'], 24)
            self.assertEqual(spec['family_search']['max_evaluations'], 16)
            self.assertTrue(spec['family_search']['coupled_block_enabled'])
            self.assertFalse(spec.get('request_budget_only', False))

    def test_no_math_blocks_all_raw_operations_and_available_discovery(self):
        spec = self.groups['no_math']
        for operation in structure_research.OPERATIONS:
            self.assertEqual(self.dispatch(spec, operation)['reason'], 'MECHANISM_OPERATION_NOT_AUTHORIZED')
        self.assertEqual(structure_research.allowed_operations(spec), [])
        actions = scientific_actions(spec)
        self.assertFalse(next(r for r in actions if r['scientific_goal'] == 'mechanism_research')['available'])
        self.assertTrue(next(r for r in actions if r.get('action') == 'search')['available'])

    def test_no_interact_raw_gate_and_other_operations_legacy_compatibility(self):
        spec = self.groups['no_interact']
        self.assertEqual(self.dispatch(spec, 'interact')['status'], 'not_applicable')
        for operation in ('inspect', 'differentiate', 'optimize', 'compare'):
            with self.subTest(operation=operation), self.assertRaises(PreparationReached):
                self.dispatch(spec, operation)
        self.assertEqual(structure_research.allowed_operations(self.full), list(structure_research.OPERATIONS))

    def test_schemas_and_operation_discovery_match_grants(self):
        for spec in self.groups.values():
            operations = structure_research.allowed_operations(spec)
            schema = question_schema(spec)
            Draft202012Validator.check_schema(schema)
            definition = schema['$defs']['ScientificStructureV4']
            if operations:
                self.assertEqual(definition['properties']['operation']['enum'], operations)
            else:
                self.assertIn('not', definition)
            raw_schema = selected_analysis_schema('mechanism_structure_v1',
                dict(operation='mechanism_structure_v1', allowed_operations=operations))
            Draft202012Validator.check_schema(raw_schema)
            with patch.object(structure_research, 'parameters', return_value=[]), \
                    patch.object(structure_research, 'finite_time_discovery', return_value={}):
                view = structure_research.discovery(spec, dict(configuration=spec['configuration']), REF)
            self.assertEqual(view['operations'], operations)
            self.assertEqual(set(view['operation_admission']), set(operations))

    def test_no_knowledge_blocks_main_reporter_cache_and_preload(self):
        spec = deepcopy(self.groups['no_knowledge'])
        self.assertEqual(spec['knowledge_manifest']['entries'], [])
        for name in ('no_math', 'no_interact'):
            self.assertEqual(self.groups[name]['knowledge_manifest'], self.full['knowledge_manifest'])
            self.assertEqual(len(self.groups[name]['knowledge_manifest']['entries']), 45)
            self.assertEqual(self.groups[name]['knowledge_manifest'], self.historical_manifest)
        spec['knowledge_manifest'] = self.full['knowledge_manifest']  # Deliberately stale fixture.
        host = SimpleNamespace(store=Mock())
        current = dict(spec=spec, retrievals=[REF])
        with patch.object(experience, 'state', return_value=current), patch.object(reporter, 'state', return_value=current):
            for reader in ('agent', 'reporter'):
                with self.assertRaisesRegex(ValueError, 'KNOWLEDGE_DISABLED'):
                    experience.retrieve(host, dict(operation='search'), reader=reader)
            with self.assertRaisesRegex(ValueError, 'KNOWLEDGE_DISABLED'):
                reporter._knowledge_receipt(host, dict(operation='read', entry_id='p3-case', revision='3'))
            self.assertEqual(experience.entries(host), [])
            self.assertIsNone(experience.retrieval_hint(host))
            self.assertEqual(experience.research_catalogue(host)['capabilities'], [])
            host.store.artifact.assert_not_called()
        schema = plan_schema(['generate', 'physical_replay', 'search', 'stop'], study=spec)
        self.assertIn('physical_replay', schema['properties']['action']['enum'])
        self.assertEqual(spec['canonical_task'], self.full['canonical_task'])

    def test_finite_physical_search_is_available_without_math_and_uses_episode_budget(self):
        for spec in self.groups.values():
            query = self.query(spec)
            self.assertTrue(passive_search.physical_response_search(spec, query))
            self.assertEqual(passive_search.problem(spec, query)['conditions'], ['all_frozen_conditions'])
            with patch.object(search, 'state', return_value=dict(spec=spec)), \
                    patch('tools.research.budget.capacity', return_value=dict(admitted=32)) as capacity, \
                    patch.object(analysis, 'admission', side_effect=AssertionError('No optional math budget')):
                self.assertEqual(search.search_admission(SimpleNamespace(), query, 16)['admitted'], 16)
                self.assertEqual(capacity.call_args.args[1], 32)

    def test_search_physical_adapter_calls_no_math_and_reuses_checkpoint(self):
        spec = self.groups['no_math']; query = self.query(spec)
        host = SimpleNamespace(store=Mock())
        host.store.artifact.return_value = dict(status='evaluated', diagnostic_task_gap=dict(constraints=[
            dict(signal='low', observed_value=.004, passed=False, normalized_violation=.2),
            dict(signal='maximum_contacts', observed_value=0, passed=True, normalized_violation=None),
            dict(signal='paired_mechanism', observed_value=None, passed=None)]))
        proposal = dict(candidate=REF)
        with patch.object(passive_search, 'state', return_value=dict(spec=spec)), \
                patch('tools.research.physical_replay.dispatch', return_value=dict(reference=REF)) as physical, \
                patch.object(analysis, 'dispatch', side_effect=AssertionError('No mathematical Worker')):
            for _ in range(2):
                result = passive_search.evaluate(host, query, proposal, 'offline', Mock(), Mock())
                self.assertEqual(result['actual_mathematical_evaluations'], 0)
                self.assertEqual(result['proxy_values']['task_violation'], .2)
                self.assertEqual(result['task_acceptance'], 'unmeasured')
            physical.assert_called_once()
            self.assertIsNone(physical.call_args.args[1].validation_source)

    def test_main_search_schema_and_compiler_keep_no_math_physical_route(self):
        spec = self.groups['no_math']
        payload = dict(research_goal='passive_structure_research', design_variable_groups=['lengths'],
            screening_fidelity='screening', evaluation_model='passive_task_response',
            control_treatment='no_active_control', proxy_objective='task_violation',
            structure_search_effort=dict(max_proposals=24, max_evaluations=16),
            segment_counts=[4], tendon_counts=[4])
        schema = plan_schema(['search'], study=spec)
        definition = {**schema['$defs']['ScientificStructureSearch'], '$defs':schema['$defs']}
        Draft202012Validator(definition).validate(payload)
        plan = dict(action='search', search=payload, decision=dict(hypothesis_id='offline-fixture'),
            **{k:'Offline fixture only' for k in ('hypothesis','expected_observation','weakening_observation',
                                                'fixed_conditions','stopping_condition','interpretation')})
        with patch.object(structure_intent, 'state', return_value=dict(spec=spec)), \
                patch.object(search, 'state', return_value=dict(spec=spec)), \
                patch('tools.research.budget.capacity', return_value=dict(admitted=32)), \
                patch.object(search, 'search_problem', side_effect=PreparationReached):
            with self.assertRaises(PreparationReached):
                structure_intent.compile_search(SimpleNamespace(), plan, 'offline')

    def test_coupled_wrapper_cannot_bypass_interact_gate(self):
        spec = self.groups['no_interact']
        query = SimpleNamespace(analysis=SimpleNamespace(), family_space_identity=spec['family_space_identity'],
                                evaluation_mode='passive_task_response')
        with patch.object(search, 'state', return_value=dict(spec=spec)), \
                patch.object(search, 'verify_candidate', side_effect=AssertionError('No preparation')):
            with self.assertRaisesRegex(ValueError, 'MECHANISM_OPERATION_NOT_AUTHORIZED'):
                search.coupled_problem(SimpleNamespace(), query, 4)

    def test_invalid_operation_lists_rejected(self):
        original = config.read
        for operations in ([], ['inspect', 'inspect'], ['unknown'], 'inspect'):
            def read(path):
                value = original(path)
                if Path(path).resolve() == self.source:
                    value['mechanism_operations'] = operations
                return value
            with self.subTest(operations=operations), patch.object(config, 'read', side_effect=read):
                with self.assertRaisesRegex(ValueError, 'EXPLICIT_SUPPORTED_MECHANISM_OPERATIONS_REQUIRED'):
                    config.resolve(self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
