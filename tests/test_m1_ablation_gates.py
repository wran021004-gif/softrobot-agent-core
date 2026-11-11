"""Offline M1 gate regressions. Fixtures never represent scientific evidence.

Set M1_ABLATION_CONFIG_DIR to the existing research repository's M1 directory.
No Host, Store or Agent is created; all admitted execution stops at a Mock.
"""
import builtins
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tools.research import analysis, conditions, config, feedback, physical_replay, task_constraints
from tools.research.agent import plan_schema
from tools.research.contracts import AnalysisRequest, ControlSeedRequest, PhysicalReplayRequest
from tools.research.nonlinear_capability import DIRECT, T1, T1_OPERATION
from tools.research.scientific_intent import control_method_choices, question_schema
from tools.platform_registry import registry


REF = dict(artifact_id='0' * 64, media_type='application/json')
original_import = builtins.__import__


def no_mujoco(name, *args, **kwargs):
    if name == 'mujoco' or name.startswith('mujoco.'):
        raise AssertionError('No MuJoCo in offline gate tests')
    return original_import(name, *args, **kwargs)


def setUpModule():
    global offline_patches
    offline_patches = ExitStack()
    offline_patches.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No Worker')))
    offline_patches.enter_context(patch('socket.socket.connect', side_effect=AssertionError('No network')))
    offline_patches.enter_context(patch('builtins.__import__', side_effect=no_mujoco))
    offline_patches.enter_context(patch('platform.machine', return_value='AMD64'))


def tearDownModule():
    offline_patches.close()


class AdmissionReached(Exception):
    """Stop before candidate preparation, baseline creation or execution."""


class M1AblationGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get('M1_ABLATION_CONFIG_DIR'):
            raise unittest.SkipTest('Set M1_ABLATION_CONFIG_DIR to the existing M1 sources')
        cls.directory = Path(os.environ['M1_ABLATION_CONFIG_DIR']).resolve()
        cls.full_path = cls.directory / 'study_m1_core_full_v1.json'
        cls.original_full_sha = hashlib.sha256(cls.full_path.read_bytes()).digest()
        cls.full = config.resolve(cls.full_path)
        cls.no_model = config.resolve(cls.directory / 'ablation_m1_no_model_based_control.json')
        cls.no_probe = config.resolve(cls.directory / 'ablation_m1_no_automated_physical_probe.json')

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(cls.full_path.read_bytes()).digest() == cls.original_full_sha

    def request(self, operation):
        return AnalysisRequest.model_validate(dict(
            candidate=REF, operation=operation, model_source='mujoco',
            operating_point='standardized_initial_pretension', protocol=self.full['analysis_protocol'],
            control_optimization=dict(source=REF, settings=dict(
                version='local_control_search_v2', method='response', correction_window_s=[0, .6],
                knots_s=[0, .3, .6], coefficient_limit_n=8, difference_step_n=.08,
                initial_radius_n=2, minimum_radius_n=.0008, iterations=100, evaluation_requests=180))))

    def dispatch_analysis(self, spec, operation):
        host = SimpleNamespace(run_id='offline-fixture', store=Mock())
        host.store.lookup.return_value = None
        with patch.object(analysis, 'state', return_value=dict(spec=spec)), \
                patch.object(analysis, 'verify_candidate', side_effect=AdmissionReached) as prepare, \
                patch.object(analysis, 'calculate', side_effect=AssertionError('No calculation')) as calculate:
            result = analysis.dispatch(host, self.request(operation), 'offline', guard=Mock())
            prepare.assert_not_called()
            calculate.assert_not_called()
            return result

    def test_configs_preserve_science_and_other_analysis(self):
        for spec in (self.no_model, self.no_probe):
            with self.subTest(study=spec['study_id']):
                for key in ('capabilities', 'allowed_plan_actions', 'family_space', 'candidate_initialization',
                            'task_conditions', 'analysis_protocol', 'native_control_limits', 'knowledge',
                            'runtime', 'budgets', 'confirmation', 'canonical_task'):
                    self.assertEqual(spec[key], self.full[key], key)
                for key in ('robot', 'task', 'policy', 'seed'):
                    self.assertEqual(spec['configuration'][key], self.full['configuration'][key], key)
                evaluator = spec['configuration']['task']['evaluator']
                registry().get(evaluator['extension_id'], evaluator['version'], 'evaluator').resolve()
        self.assertIn('analysis', self.no_model['capabilities'])
        self.assertEqual(self.no_model['mathematical_methods']['mechanism_structure_v1'],
                         self.full['mathematical_methods']['mechanism_structure_v1'])

    def test_no_model_rejects_both_raw_operations_before_preparation(self):
        for operation in (T1_OPERATION, DIRECT):
            with self.subTest(operation=operation):
                result = self.dispatch_analysis(self.no_model, operation)
                self.assertEqual(result['reason'], 'EXPLICIT_FROZEN_MATHEMATICAL_METHOD_AUTHORIZATION_REQUIRED')

    def test_native_and_direct_grants_are_independent(self):
        for denied, allowed in ((DIRECT, T1_OPERATION), (T1_OPERATION, DIRECT)):
            spec = deepcopy(self.full)
            spec['mathematical_methods'][DIRECT if denied == DIRECT else T1] = None
            self.assertEqual(self.dispatch_analysis(spec, denied)['status'], 'not_applicable')
            with self.assertRaises(AdmissionReached):
                self.dispatch_analysis(spec, allowed)

    def test_no_probe_keeps_native_direct_and_legacy_full(self):
        legacy = deepcopy(self.full)
        legacy['mathematical_methods'].pop(DIRECT)
        self.assertNotIn('control_initialization_methods', self.full)
        for spec in (self.no_probe, self.full, legacy):
            for operation in (T1_OPERATION, DIRECT):
                with self.subTest(study=spec['study_id'], operation=operation), self.assertRaises(AdmissionReached):
                    self.dispatch_analysis(spec, operation)

    def test_probe_denied_before_clone_delegation_or_physics(self):
        host = SimpleNamespace()
        request = ControlSeedRequest(candidate=REF, condition_id='central_high', method='physical_response')
        with patch.object(physical_replay, 'state', return_value=dict(spec=self.no_probe)), \
                patch.object(conditions, 'condition_candidate') as clone, \
                patch.object(physical_replay, 'guided_seed') as guided, \
                patch.object(physical_replay, '_seed_control') as baseline, \
                patch.object(physical_replay, 'evaluate_schedule') as evaluate:
            with self.assertRaisesRegex(ValueError, 'CONTROL_INITIALIZATION_METHOD_NOT_AUTHORIZED'):
                physical_replay.seed_control(host, request, 'offline')
            for target in (clone, guided, baseline, evaluate):
                target.assert_not_called()

    def test_allowed_initialization_and_schema(self):
        for spec, method, delegate in ((self.no_probe, 'baseline', '_seed_control'),
                                      (self.no_model, 'physical_response', 'guided_seed'),
                                      (self.full, 'physical_response', 'guided_seed')):
            with self.subTest(study=spec['study_id'], method=method), \
                    patch.object(physical_replay, 'state', return_value=dict(spec=spec, numerical_s=0)), \
                    patch.object(physical_replay, 'update'), \
                    patch.object(physical_replay, delegate, side_effect=AdmissionReached):
                with self.assertRaises(AdmissionReached):
                    physical_replay.seed_control(SimpleNamespace(), ControlSeedRequest(candidate=REF, method=method))
        for spec in (self.no_probe, self.no_model, self.full):
            seed = plan_schema(['initialize_control'], study=spec)['$defs']['ControlSeedRequest']
            self.assertEqual('physical_response' in seed['properties']['method']['enum'], spec != self.no_probe)
            self.assertIn('baseline', seed['properties']['method']['enum'])

    def test_common_replay_and_joint_select_paths(self):
        for spec in (self.no_model, self.no_probe):
            host = SimpleNamespace(run_id='offline-fixture', store=Mock())
            host.store.artifact.return_value = dict(source_kind='explicit_control_schedule_v1',
                task_acceptance='unmeasured', provenance=dict(fixture=True), trajectory={})
            for action in ('initialize_control', 'physical_replay', 'select'):
                self.assertIn(action, spec['allowed_plan_actions'])
            with patch.object(physical_replay, 'guard'), \
                    patch.object(physical_replay, 'state', return_value=dict(spec=spec)), \
                    patch.object(physical_replay, 'verify_candidate', return_value=dict(configuration=spec['configuration'])), \
                    patch.object(physical_replay, 'binding') as binding, \
                    patch('tools.research.budget.capacity', return_value=dict(admitted=1)), \
                    patch.object(feedback, 'experiment_preflight', side_effect=AdmissionReached):
                with self.assertRaises(AdmissionReached):
                    physical_replay.dispatch(host, PhysicalReplayRequest(candidate=REF, source=REF), 'offline')
                binding.assert_called_once()
            with patch('tools.research.state.state', return_value=dict(spec=spec)), \
                    patch.object(conditions, 'joint_assessment', return_value=dict(fixture=True)) as assess:
                result = feedback.eligibility(host, [REF, REF, REF], selection=True)
                self.assertTrue(result['eligible'])
                assess.assert_called_once()

    def test_control_catalog_and_question_schema_match_independent_grants(self):
        direct_off = deepcopy(self.full)
        direct_off['mathematical_methods'][DIRECT] = None
        for spec, expected in ((self.no_model, set()), (self.no_probe, {T1, DIRECT}), (direct_off, {T1})):
            candidate = dict(configuration=spec['configuration'])
            current = dict(spec=spec, research_status='ready', candidates=dict(fixture=REF), analysis_results=[])
            host = SimpleNamespace(store=Mock(), run_id='offline-fixture')
            host.store.artifact.return_value = candidate
            with patch('tools.research.state.state', return_value=current), \
                    patch('tools.research.state.protected', return_value=False), \
                    patch('tools.research.design.verify_candidate', return_value=candidate), \
                    patch('tools.research.optimal_capability.candidate_methods', return_value={}), \
                    patch('tools.research.research_context.mathematics_authorization',
                          return_value=dict(registered_study_scope_authorized=True)), \
                    patch.object(physical_replay, 'legal_control_sources', return_value=[]), \
                    patch.object(task_constraints, 'mechanism_interface', return_value=False):
                snapshot = dict(science_budget=dict(remaining_mathematical=16, remaining_physical=18,
                                                     remaining_full_replays=18, available_full_replays=18))
                view = task_constraints.mathematical_method_view(host, REF, budget_snapshot=snapshot)
            choices = control_method_choices(view)
            self.assertEqual({r['method'] for r in choices if r['selectable']}, expected)
            schema = question_schema(spec, candidate, control_methods=choices)
            methods = schema['$defs']['ScientificControlV4']['properties']['numerical_method']['enum']
            self.assertEqual(set(methods) - {None}, expected)

    def test_invalid_initialization_whitelists_rejected_by_parser(self):
        original = config.read
        for methods in ([], ['baseline', 'baseline'], ['invented'], 'baseline'):
            def read(path):
                value = original(path)
                if Path(path).resolve() == self.full_path:
                    value['control_initialization_methods'] = methods
                return value
            with self.subTest(methods=methods), patch.object(config, 'read', side_effect=read):
                with self.assertRaisesRegex(ValueError, 'EXPLICIT_SUPPORTED_CONTROL_INITIALIZATION_METHODS_REQUIRED'):
                    config.resolve(self.full_path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
