"""Offline transport and failed-initial-request recovery; no Host or Study."""
import builtins
from contextlib import ExitStack, nullcontext
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.research import config, provider, session_handoff
from tools.state_io import digest


class Cursor:
    def fetchone(self):
        return (0,)

    def __iter__(self):
        return iter(())


class MemoryStore:
    def __init__(self, current):
        self.current = deepcopy(current)
        self.values = {}
        self.events_list = []
        self.snapshot = dict(input=deepcopy(current['spec']['configuration']))

    def transaction(self):
        return nullcontext(self)

    def execute(self, *args):
        return Cursor()

    def session(self, *args):
        return dict(state=deepcopy(self.current), snapshot=deepcopy(self.snapshot))

    def put(self, db, value):
        ref = dict(artifact_id=digest(value), media_type='application/json')
        self.values[ref['artifact_id']] = deepcopy(value)
        return ref

    def artifact(self, ref, **kwargs):
        value = deepcopy(self.values[ref['artifact_id']])
        return json.dumps(value).encode() if kwargs.get('raw') else value

    def update_state(self, db, run_id, value):
        self.current = deepcopy(value)

    def event(self, db, run_id, kind, status, outputs):
        self.events_list.append(dict(kind=kind, status=status, outputs=outputs))

    def events(self, *args):
        return deepcopy(self.events_list)

    def lookup(self, *args):
        return dict(receipt=json.dumps(dict(execution_status='failed')))


class Account3Resume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get('P3_ABLATION_CONFIG_DIR')
        if not root:
            raise unittest.SkipTest('Set P3_ABLATION_CONFIG_DIR to the committed research sources')
        cls.spec = config.resolve(Path(root) / 'study_p3_ablation_no_math_v1.json')

    def setUp(self):
        self.offline = ExitStack()
        self.addCleanup(self.offline.close)
        self.offline.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No Worker')))
        self.offline.enter_context(patch('socket.socket.connect', side_effect=AssertionError('No Provider')))
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == 'mujoco' or name.startswith('mujoco.'):
                raise AssertionError('No MuJoCo')
            return original_import(name, *args, **kwargs)

        self.offline.enter_context(patch('builtins.__import__', side_effect=guarded_import))

    def transport(self, endpoint='http://127.0.0.1:8789/v1', model=None):
        current = dict(spec=deepcopy(self.spec), pilot=dict(provider=deepcopy(self.spec['runtime']['provider']), live_model_requests=1),
            pending=None, rl_runs={}, research_status='stopped')
        store = MemoryStore(current)
        host = SimpleNamespace(store=store, run_id=self.spec['study_id'], reg=object())
        target = deepcopy(self.spec['runtime']['provider'])
        target['base_url'] = endpoint
        if model:
            target['model'] = model
        scope = dict(study_id=host.run_id, resolved_identity=self.spec['resolved_identity'],
            previous_provider_identity=digest(self.spec['runtime']['provider']), provider=target,
            credentials_reference='~/.softrobot-agent/chatgpt-api-account3.json')
        approval = dict(version='provider_transport_approval_v1', approved=True,
            source='Synthetic explicit account3 authorization', scope=scope, scope_identity=digest(scope))
        return host, approval

    def test_same_gateway_instance_change_preserves_science_and_requests(self):
        host, approval = self.transport()
        before = deepcopy(host.store.current)
        with patch('tools.platform_tasks.compile_input', return_value={}), \
                patch.object(provider, 'pending', return_value=[]):
            result = provider.transition_transport(host, approval)
        after = host.store.current
        self.assertEqual(after['spec']['runtime']['provider']['base_url'], 'http://127.0.0.1:8789/v1')
        self.assertEqual(after['spec']['budgets'], before['spec']['budgets'])
        for key in ('canonical_task', 'family_space', 'fidelity_policy', 'knowledge_manifest', 'mathematical_methods'):
            self.assertEqual(after['spec'][key], before['spec'][key], key)
        for key in ('robot', 'task'):
            self.assertEqual(after['spec']['configuration'][key], before['spec']['configuration'][key])
        self.assertEqual(after['pilot']['live_model_requests'], 1)
        self.assertEqual(after['research_status'], 'stopped')
        self.assertEqual(result['provider_requests_sent'], 0)
        self.assertTrue(after['validation_extension_pending_binding'])
        saved = host.store.artifact(result['reference'])
        self.assertEqual(host.store.artifact(saved['previous_state']), before)
        self.assertTrue(saved['all_costs_and_failures_retained'])

    def test_remote_endpoint_and_model_change_still_rejected(self):
        for endpoint, model in (('http://example.com:8789/v1', None),
                                ('http://127.0.0.1:8789/v1', 'unapproved-model')):
            with self.subTest(endpoint=endpoint, model=model):
                host, approval = self.transport(endpoint, model)
                before = deepcopy(host.store.current)
                with self.assertRaisesRegex(ValueError, 'TRANSPORT_ONLY_SAME_MODEL_AND_RESEARCH_SETTINGS_REQUIRED'):
                    provider.transition_transport(host, approval)
                self.assertEqual(host.store.current, before)
                self.assertEqual(host.store.events_list, [])

    def initial_request(self, status=429, corrected=True, rebound=True, tool_output=False):
        current = dict(spec=deepcopy(self.spec), pending=None,
            pilot=dict(framework_session_id='original-session'), research_status='ready')
        store = MemoryStore(current)
        host = SimpleNamespace(store=store, run_id=self.spec['study_id'])
        messages = [dict(role='user', content=[dict(text=session_handoff.INVOCATION_PROMPT)])]
        wire = dict(messages=[dict(role='system', content='Synthetic system'),
            dict(role='user', content=session_handoff.INVOCATION_PROMPT),
            dict(role='user', content='CURRENT_RESEARCH_PACKET\n{}')])
        wire_ref = store.put(None, wire)
        metadata = store.put(None, dict(purpose='conversation', request=wire_ref,
            endpoint='http://127.0.0.1:8787/v1/chat/completions'))
        body_ref = store.put(None, dict(error=dict(code='subscription_sharing_usage_limit_exceeded')))
        store.events_list = [dict(kind='r3_request', request_id='failed-request', sequence=1, outputs=[metadata])]
        if corrected:
            store.events_list.append(dict(kind='provider_transport_transition', status='authorized', sequence=2))
        if rebound:
            store.events_list.append(dict(kind='implementation_binding', status='committed', sequence=3))
        if tool_output:
            store.events_list.append(dict(kind='candidate_constructed', status='saved', sequence=4))
        agent = SimpleNamespace(messages=messages, _session_manager=SimpleNamespace(session_id='original-session'))
        reception = dict(http_status=status, body=body_ref)
        return host, agent, reception, wire

    def recover(self, host, agent, reception, wire):
        with patch.object(session_handoff, 'state', return_value=host.store.current), \
                patch.object(provider, 'received', return_value=reception), \
                patch.object(provider, 'model_messages', return_value=wire['messages'][:-1]):
            return session_handoff.trusted_history(host, agent)

    def test_corrected_initial_429_reuses_exact_prompt_and_failed_receipt(self):
        host, agent, reception, wire = self.initial_request()
        before = deepcopy(host.store.current)
        self.assertEqual(self.recover(host, agent, reception, wire), 'rejected_initial_request')
        self.assertEqual(host.store.current, before)
        self.assertEqual(len(agent.messages), 1)
        self.assertEqual(agent.messages[0]['role'], 'user')

    def test_unapproved_unbound_successful_or_executed_request_cannot_be_skipped(self):
        for arguments in (dict(corrected=False), dict(rebound=False), dict(status=200), dict(tool_output=True)):
            with self.subTest(arguments=arguments):
                host, agent, reception, wire = self.initial_request(**arguments)
                with self.assertRaisesRegex(ValueError, 'SDK_HISTORY_HAS_NO_TRUSTED_STORE_ANCHOR'):
                    self.recover(host, agent, reception, wire)

    def test_changed_initial_prompt_cannot_be_skipped(self):
        host, agent, reception, wire = self.initial_request()
        agent.messages[0]['content'][0]['text'] = 'Changed prompt'
        with self.assertRaisesRegex(ValueError, 'SDK_HISTORY_HAS_NO_TRUSTED_STORE_ANCHOR'):
            self.recover(host, agent, reception, wire)


if __name__ == '__main__':
    unittest.main()
