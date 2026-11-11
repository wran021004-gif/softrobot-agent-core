"""Offline regressions: schema/compilation and user-scoped temporal authorization."""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
import json
import sqlite3
import tempfile
import unittest
from uuid import uuid4

from tools.platform_store import Store, encode
from tools.research.budget import authorize_native_knot_limit
from tools.research.contracts import ScientificQuestionV4
from tools.research.scientific_intent import control_resolution_options, control_settings, project_control_effort
from tools.state_io import digest


def spec(limit=4):
    return dict(mode='formal_research',capabilities=['analysis'],resolved_identity='original',
        native_control_limits=dict(knots_s=limit,evaluation_requests=800,iterations=100),
        analysis_protocol=dict(duration_s=.6,period_s=.02),
        budgets=dict(provider_requests=73,mathematical_evaluations=16,physical_launches=18),
        task={'frozen':'same original physical task'})


class ResolutionTests(unittest.TestCase):
    def choices(self,limit):
        schema=ScientificQuestionV4.model_json_schema()
        project_control_effort(schema,spec(limit))
        return schema['$defs']['ScientificControlEffort']['properties']['resolution']['enum']

    def test_schema_never_advertises_over_grant_resolution(self):
        self.assertEqual(self.choices(4),['coarse'])
        self.assertEqual(self.choices(5),['coarse','moderate'])
        self.assertEqual(self.choices(30),['coarse','moderate','fine','very_fine','control_grid'])

    def test_original_grant_still_rejects_higher_resolution(self):
        for resolution in ['moderate','fine','very_fine','control_grid']:
            with self.subTest(resolution=resolution),self.assertRaisesRegex(ValueError,'REQUESTED_RESOLUTION_EXCEEDS_FROZEN_KNOT_GRANT'):
                control_settings(spec(),dict(resolution=resolution,exploration='broad',evaluation_requests=800),channels=6,physical_limit_n=8)
        self.assertEqual(control_resolution_options(spec())['maximum_knots'],4)

    def test_authorized_grid_has_only_effective_inputs_and_keeps_other_limits(self):
        settings=control_settings(spec(30),dict(resolution='control_grid',exploration='broad',evaluation_requests=800),channels=6,physical_limit_n=8)
        self.assertEqual(len(settings.knots_s),30)
        self.assertEqual(settings.knots_s[0],0)
        self.assertAlmostEqual(settings.knots_s[-1],.58)
        self.assertNotIn(.6,settings.knots_s)
        self.assertEqual(settings.evaluation_requests,800)
        self.assertEqual(settings.iterations,100)
        self.assertEqual(settings.coefficient_limit_n,8)
        with self.assertRaisesRegex(ValueError,'CONTROL_GRID_REQUIRES_FULL_TASK_SCOPE'):
            control_settings(spec(30),dict(resolution='control_grid',exploration='broad',evaluation_requests=800),window=(.54,.6),channels=6,physical_limit_n=8)

    def test_all_advertised_choices_compile_under_current_full_task(self):
        for limit in [4,5,9,17,30]:
            for resolution in self.choices(limit):
                with self.subTest(limit=limit,resolution=resolution):
                    settings=control_settings(spec(limit),dict(resolution=resolution,exploration='local_refinement',evaluation_requests=400),channels=6,physical_limit_n=8)
                    self.assertLessEqual(len(settings.knots_s),limit)
                    self.assertEqual(len(set(settings.knots_s)),len(settings.knots_s))
                    self.assertEqual(settings.coefficient_limit_n,.8)


class UnitStore(Store):
    def connect(self,readonly=False):
        db=super().connect(readonly)
        if not hasattr(self,'connections'):self.connections=[]
        self.connections.append(db)
        return db

    def check_root(self,db):
        pass  # Isolated SQLite fixture; production authority binding is not changed.


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        # Default mkdir permissions also work in restricted Windows workspaces;
        # Python 3.13's private (0700) TemporaryDirectory ACL can exclude the sandbox.
        root=Path(tempfile.gettempdir())/('temporal-unit-'+uuid4().hex);root.mkdir()
        self.store=UnitStore(root);self.host=SimpleNamespace(store=self.store,run_id='unit-study')
        def cleanup():
            for db in getattr(self.store,'connections',[]):db.close()
            for suffix in ['','-journal','-wal','-shm']:
                self.store.db.with_name(self.store.db.name+suffix).unlink(missing_ok=True)
            root.rmdir()
        self.addCleanup(cleanup)
        self.initial=dict(spec=spec(),pending=None,pilot=dict(unconsumed_response=None),research_status='ready',
            candidates={'c':{'artifact_id':'preserved'}},analysis_results=['preserved-analysis'],physical_replays=['preserved-replay'],
            mathematical_evaluations=6)
        with closing(self.store.connect()) as db,db:
            db.executescript('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE artifacts(id TEXT PRIMARY KEY,media TEXT,body BLOB); CREATE TABLE sessions(run_id TEXT PRIMARY KEY,snapshot TEXT,status TEXT,state TEXT); CREATE TABLE calls(run_id TEXT,caller TEXT,status TEXT,receipt TEXT,charged TEXT); CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,body TEXT);')
            db.execute('INSERT INTO meta VALUES (?,?)',('config',encode(dict(project_id='unit-project'))))
            snap=self.store.put(db,dict(input=dict(policy=dict(budget=dict(model_calls=73)))))
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)',('unit-study',snap.artifact_id,'running',encode(self.initial)))
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?)',('unit-study','research-provider','completed','{}',encode({'model_calls':54})))

    def approval(self,**overrides):
        scope=dict(study_id='unit-study',resolved_identity='original',previous_knot_limit=4,new_knot_limit=30)
        scope.update(overrides)
        return dict(version='native_knot_limit_approval_v1',approved=True,source='Explicit test user instruction',scope=scope,scope_identity=digest(scope))

    def test_changes_only_authorized_limit_and_retains_counts_evidence_and_receipts(self):
        approval=self.approval();result=authorize_native_knot_limit(self.host,approval)
        current=self.store.session('unit-study')['state'];updated=deepcopy(current['spec'])
        self.assertEqual(updated.pop('native_control_limits')['knots_s'],30)
        self.assertEqual(current['spec']['budgets'],self.initial['spec']['budgets'])
        self.assertEqual(current['spec']['task'],self.initial['spec']['task'])
        for key in ['candidates','analysis_results','physical_replays','mathematical_evaluations']:
            self.assertEqual(current[key],self.initial[key])
        self.assertTrue(current['validation_extension_pending_binding'])
        with closing(self.store.connect(True)) as db:
            self.assertEqual(json.loads(db.execute('SELECT charged FROM calls').fetchone()[0]),{'model_calls':54})
        self.assertTrue(result['requires_current_identity_research_authorization'])
        self.assertEqual(authorize_native_knot_limit(self.host,approval)['already_applied'],True)
        self.assertEqual(len(self.store.session('unit-study')['state']['native_knot_limit_authorizations']),1)

    def test_invalid_scope_or_unsettled_state_cannot_change_limit(self):
        for scope in [dict(study_id='other'),dict(resolved_identity='other'),dict(previous_knot_limit=5),dict(new_knot_limit=65),dict(new_knot_limit=4),dict(new_knot_limit=True)]:
            with self.subTest(scope=scope),self.assertRaises(ValueError):authorize_native_knot_limit(self.host,self.approval(**scope))
            self.assertEqual(self.store.session('unit-study')['state'],self.initial)
        for change in [dict(pending={'execution':'unknown'}),dict(pilot=dict(unconsumed_response={'saved':True})),dict(research_status='stopped'),dict(selected={'solution':'saved'}),dict(success_gate={'passed':True})]:
            current={**self.initial,**change}
            with self.store.transaction() as db:self.store.update_state(db,'unit-study',current)
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'SETTLED_NONSUCCESS'):authorize_native_knot_limit(self.host,self.approval())
            self.assertEqual(self.store.session('unit-study')['state'],current)


if __name__=='__main__':unittest.main()
