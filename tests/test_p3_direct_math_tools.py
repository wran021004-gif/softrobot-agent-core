"""Offline synthetic fixtures only; no Study, agent, Worker, Provider or MuJoCo."""
import builtins
from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from jsonschema import Draft202012Validator
from tools.research import analysis,config,direct_math,experience,passive_search,structure_research
from tools.research.agent import project_math_tools,tool_directory
from tools.research.contracts import AnalysisRequest,DirectMathAPI,FamilyMixedSearch

REF=dict(artifact_id='0'*64,media_type='application/json')
ROW=dict(parameter_id='segments.0.length_m',minimum=.1,maximum=.9,current_value=.5,
    unit='m',continuous_perturbation=True,effective_in_current_execution=True)
IMPORT=builtins.__import__


def no_mujoco(name,*args,**kwargs):
    if name=='mujoco' or name.startswith('mujoco.'):raise AssertionError('No MuJoCo in offline tests')
    return IMPORT(name,*args,**kwargs)


def setUpModule():
    global offline
    offline=ExitStack()
    for name in ('socket.socket.connect','subprocess.Popen','tools.service_execution._run_contained'):
        offline.enter_context(patch(name,side_effect=AssertionError('No network or Worker')))
    offline.enter_context(patch('builtins.__import__',side_effect=no_mujoco))
    offline.enter_context(patch('platform.machine',return_value='AMD64'))


def tearDownModule():offline.close()


class DirectMathTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=Path(os.environ['P3_ABLATION_CONFIG_DIR'])
        cls.full=config.resolve(cls.directory/'study_p3_full_selective_v2.json')
        cls.direct=config.resolve(cls.directory/'study_p3_direct_math_tools_v1.json')

    def request(self,function,**kw):
        return DirectMathAPI(function=function,target=dict(quantity='constraint_kkt_residual',goal='decrease'),
            load_condition='unloaded',**kw)

    def query(self,request):
        return AnalysisRequest(candidate=REF,operation=direct_math.METHOD,model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=self.direct['analysis_protocol'],direct_math=request)

    def candidate(self):
        return dict(_reference=REF,configuration=self.direct['configuration'],parameters={},generation_version='fixture')

    def prepare(self,request,sources=()):
        caps=dict(status='supported',evaluation=dict(finite_time_structure_response=True))
        with patch.object(structure_research,'parameters',return_value=[ROW]),patch('tools.research_tasks.task_adapter') as adapter:
            adapter.return_value.physical_capabilities.return_value=caps
            return direct_math.prepare(self.direct,self.candidate(),request,list(sources))

    def test_config_only_interface_identity_differences(self):
        for key in ('canonical_task','family_space','runtime','family_search','fidelity_policy',
                    'knowledge_manifest','budgets','execution_instructions','initial_structure_strategy'):
            self.assertEqual(self.full[key],self.direct[key],key)
        for key in ('robot','task','discretization'):self.assertEqual(self.full['configuration'].get(key),self.direct['configuration'].get(key))
        self.assertNotEqual(self.full['study_id'],self.direct['study_id'])
        self.assertNotEqual(self.full['evidence_destination'],self.direct['evidence_destination'])
        self.assertEqual(self.full['base_commit'],self.direct['base_commit'])
        self.assertEqual(self.direct['initial_structure_strategy'],'agent_choice')
        self.assertEqual([self.direct['budgets'][k] for k in ('provider_requests','protected_provider_requests','mathematical_evaluations','physical_launches','public_operations')],[200,4,100,150,800])
        self.assertEqual(self.direct['family_search']['max_proposals'],24)
        self.assertEqual(self.direct['family_search']['max_evaluations'],16)
        self.assertEqual(self.direct['research_decisions']['history'],[])
        self.assertEqual(self.direct['research_decisions']['control_seeds'],[])

    def test_five_high_level_operations_full_only(self):
        self.assertEqual(structure_research.allowed_operations(self.full),list(structure_research.OPERATIONS))
        self.assertEqual(structure_research.allowed_operations(self.direct),[])
        for op in structure_research.OPERATIONS:
            q=AnalysisRequest(candidate=REF,operation='mechanism_structure_v1',model_source='mujoco',
                operating_point='standardized_initial_pretension',protocol=self.direct['analysis_protocol'],
                mechanism_study=dict(operation=op,target=dict(quantity='constraint_kkt_residual',goal='decrease'),
                    point_semantics='re_equilibrated',max_evaluations=8,
                    parameter_paths=['segments.0.length_m','segments.1.length_m'] if op=='interact' else []))
            with patch.object(analysis,'state',return_value=dict(spec=self.direct)),patch.object(analysis,'verify_candidate') as verify:
                h=SimpleNamespace(store=Mock(),run_id='offline');h.store.lookup.return_value=None
                value=analysis.dispatch(h,q,'fixture',guard=Mock())
                self.assertEqual(value['reason'],'MECHANISM_OPERATION_NOT_AUTHORIZED');verify.assert_not_called()

    def test_main_schema_projection_and_route_directory(self):
        schema=direct_math.schema(self.direct);Draft202012Validator.check_schema(schema)
        self.assertEqual(schema['properties']['function']['enum'],list(direct_math.APIS))
        self.assertNotIn('operation',schema['properties'])
        for spec,allowed in ((self.full,'research_analysis'),(self.direct,'research_math_api')):
            registry={k:SimpleNamespace(tool_spec=dict(description='fixture',inputSchema={'json':schema})) for k in ('research_analysis','research_math_api')}
            project_math_tools(spec,registry,0);self.assertEqual(set(registry),{allowed})
            with patch('tools.research.agent.state',return_value=dict(spec=spec)):
                self.assertEqual([r['tool'] for r in tool_directory(Mock(),registry)],[allowed])
            project_math_tools(spec,registry,100);self.assertEqual(registry,{})

    def test_same_skill_is_full_main_prompt_content(self):
        prompts=[experience.add_main_guidance('system',s) for s in (self.full,self.direct)]
        self.assertEqual(prompts[0],prompts[1]);self.assertIn('FROZEN_MAIN_RESEARCH_GUIDANCE',prompts[0])
        self.assertIn('competing explanations',prompts[0]);self.assertIn('not_comparable',prompts[0])
        self.assertNotIn('0.0105',prompts[0]);self.assertNotIn('candidate_606',prompts[0])
        self.assertEqual(len(self.direct['knowledge_manifest']['entries']),46)
        guidance=experience.main_context(self.direct);self.assertEqual(guidance[0]['revision'],'1')
        self.assertEqual(len(guidance[0]['guidance']['workflow']),7)

    def test_ordinary_physics_ignores_math_grant_and_never_analyzes(self):
        for spec in (self.full,self.direct):
            q=FamilyMixedSearch(version='family_mixed_search_v1',family_space_identity=spec['family_space_identity'],
                variable_groups=['lengths'],segment_counts=[2],tendon_counts=[4],screening_fidelity='screening',
                objective='task_violation',operating_point='standardized_initial_pretension',
                evaluation_mode='passive_task_response',max_proposals=24,max_evaluations=16)
            self.assertTrue(passive_search.physical_response_search(spec,q))
            with patch.object(passive_search,'state',return_value=dict(spec=spec)),patch.object(passive_search,'evaluate_physical',return_value={'physical':True}) as physical,patch.object(analysis,'dispatch',side_effect=AssertionError('No mathematical inspect')):
                out=passive_search.evaluate(Mock(),q,{},'fixture',Mock(),Mock())
                self.assertTrue(out['physical']);physical.assert_called_once()

    def test_illegal_inputs_and_domains_rejected_before_numerics(self):
        for request in (self.request('model_evaluate',parameter_paths=['unregistered']),
                        self.request('model_evaluate',parameter_paths=[ROW['parameter_id']],parameter_values={ROW['parameter_id']:2.}),
                        self.request('finite_difference',parameter_paths=[ROW['parameter_id']],max_evaluations=1)):
            with self.assertRaises(ValueError),patch.object(structure_research,'model_evaluator',side_effect=AssertionError('No numerical execution')):self.prepare(request)
        with self.assertRaises(ValueError):self.request('arbitrary_python')

    def test_evaluation_and_episode_bounds_are_attributed_separately(self):
        q=self.request('finite_difference',parameter_paths=[ROW['parameter_id']],max_evaluations=5)
        ctx=self.prepare(q);self.assertEqual(ctx['evaluations'],5);self.assertEqual(ctx['dynamic_cost_bound']['episodes'],0)
        q=DirectMathAPI(function='model_evaluate',target=dict(quantity='finite_time_task_violation',goal='decrease'),
            effect_semantics='finite_time_task_response',point_semantics='frozen_task_initial_state')
        ctx=self.prepare(q);self.assertEqual(ctx['evaluations'],1);self.assertEqual(ctx['dynamic_cost_bound']['episodes'],2)
        ctx=self.prepare(self.request('stencil',parameter_paths=[ROW['parameter_id']]))
        self.assertEqual(ctx['evaluations'],0)

    def test_dispatch_calls_original_worker_boundary_without_semantic_request(self):
        spec=self.direct;host=SimpleNamespace();request=self.request('model_evaluate')
        payload={**request.model_dump(mode='json'),'candidate':REF}
        with patch('tools.research.state.state',return_value=dict(spec=spec)),patch('tools.research.design.verify_candidate',return_value=self.candidate()),patch.object(analysis,'dispatch',return_value={'admitted':True}) as execute:
            for _ in range(2):self.assertTrue(direct_math.dispatch(host,payload,'fixture',guard=Mock())['admitted'])
            self.assertEqual(execute.call_count,2)
            q=execute.call_args.args[1];self.assertIsNone(q.mechanism_study);self.assertEqual(q.operation,direct_math.METHOD)

    def test_real_stencil_and_four_point_kernels_are_exposed(self):
        second={**ROW,'parameter_id':'segments.1.length_m'}
        for function,rows in (('stencil',[ROW]),('matched_points',[ROW,second])):
            request=self.request(function,parameter_paths=[r['parameter_id'] for r in rows])
            context=dict(sources=[],selected_parameters=rows,evaluations=0)
            factory=(Mock(side_effect=AssertionError('No model evaluation')),[],[],[],[],[])
            with patch.object(structure_research,'model_evaluator',return_value=factory):
                out=direct_math.calculate({}, {}, self.query(request),None,context)['direct_math']['result']
            if function=='stencil':self.assertEqual(len(out['coordinates']),4)
            else:self.assertEqual([r['label'] for r in out],['00','10','01','11'])

    def numerical_factory(self,branch=False):
        records=[]
        def evaluate(values=None):
            x=.5 if values is None else values[0]
            r=dict(record_index=len(records),parameter_values={ROW['parameter_id']:x},configuration={'task':{'physical_problem':{'mode':'passive_unilateral_equilibrium'}}},
                physics_identity='fixture',observation=dict(status='computed',value=x*x,unit='N*m'),compiled_physical_changes={'changed':True} if records else {},
                mechanics=dict(equilibrium={'equilibrium':{'active':[bool(branch and records)],'positive':[]}},
                    constraint_state=dict(qualified=True,status='smooth_fixed_active_set')))
            records.append(r);return r
        return evaluate,records,[],[],[],[.5]

    def test_real_difference_kernel_and_shared_branch_validity(self):
        request=self.request('finite_difference',parameter_paths=[ROW['parameter_id']],max_evaluations=5)
        for switched in (False,True):
            with patch.object(structure_research,'model_evaluator',return_value=self.numerical_factory(switched)),patch('tools.research_tasks.task_adapter'),patch('extensions.math_analysis.differentiation_router.select_method',return_value={'method':'finite_difference'}):
                out=direct_math.calculate({}, {},self.query(request),None,dict(sources=[],selected_parameters=[ROW]))['direct_math']['result']
            if switched:self.assertEqual(out['derivatives'],[None,None]);self.assertFalse(out['consistency']['passed'])
            else:self.assertAlmostEqual(out['derivatives'][0],1.);self.assertTrue(out['consistency']['passed'])
            self.assertFalse(out['strict_derivative'])

    def test_raw_powell_calls_existing_solver_and_missing_objective_is_withheld(self):
        request=self.request('minimize',parameter_paths=[ROW['parameter_id']],max_evaluations=8)
        factory=self.numerical_factory()
        mapping=dict(kind='normalized_linear_domain',origin=.5,minimum=.1,maximum=.9,physical_value=.5,physical_scale=.8)
        factory=(*factory[:4],[mapping],factory[-1])
        # Existing SciPy API is the only optimizer; no engine or physics is reimplemented.
        solved=SimpleNamespace(success=False,status=1,message='synthetic evaluation cap',nfev=1,x=[.49])
        def solver(objective,center,**kwargs):
            self.assertEqual(kwargs['method'],'Powell');objective([.49]);return solved
        with patch.object(structure_research,'model_evaluator',return_value=factory),patch('scipy.optimize.minimize',side_effect=solver) as minimize:
            result=direct_math.calculate({}, {},self.query(request),None,dict(sources=[],selected_parameters=[ROW]))
            self.assertEqual(result['direct_math']['result']['method'],'scipy.optimize.minimize/Powell');minimize.assert_called_once()
        def missing(values=None):return {'observation':{'value':None,'status':'unavailable','unit':'1'}}
        with patch.object(structure_research,'model_evaluator',return_value=(missing,[],[],[],[mapping],[.5])),patch('scipy.optimize.minimize') as minimize:
            result=direct_math.calculate({}, {},self.query(request),None,dict(sources=[],selected_parameters=[ROW]))
            self.assertEqual(result['direct_math']['result']['derivative_status'],'not_defined');minimize.assert_not_called()

    def test_direct_shared_math_limit_rejects_before_reservation_or_worker(self):
        h=SimpleNamespace(store=Mock(),run_id='offline');h.store.lookup.return_value=None
        s=dict(spec=self.direct,mathematical_evaluations=100)
        with patch.object(analysis,'state',return_value=s),patch.object(analysis,'verify_candidate',return_value=self.candidate()),patch.object(direct_math,'prepare',return_value={'evaluations':1}),patch('tools.research.research_context.mathematics_authorization',return_value={'registered_study_scope_authorized':True}):
            with self.assertRaisesRegex(ValueError,'ANALYSIS_AND_CONFIRMATION_BUDGET_CANNOT_FIT'):
                analysis.dispatch(h,self.query(self.request('model_evaluate')),'fixture',guard=Mock())
        h.store.reserve.assert_not_called()

    def test_real_direct_dispatch_reaches_shared_reservation_without_a_worker(self):
        class ReservationReached(Exception):pass
        h=SimpleNamespace(store=Mock(),run_id='offline',actor='fixture');h.store.lookup.return_value=None
        h.store.reserve.side_effect=ReservationReached
        candidate={**self.candidate(), 'configuration_reference':REF,'candidate_id':'fixture',
            'source_identity':'fixture','profile_identity':'fixture','generation_version':None}
        s=dict(spec=self.direct,mathematical_evaluations=0)
        with patch.object(analysis,'state',return_value=s),patch.object(analysis,'verify_candidate',return_value=candidate),patch.object(direct_math,'prepare',return_value={'evaluations':1}),patch('tools.research.research_context.mathematics_authorization',return_value={'registered_study_scope_authorized':True}),patch('extensions.tendon_family.compiler.resolve',return_value={'dofs':['fixture']}):
            with self.assertRaises(ReservationReached):
                analysis.dispatch(h,self.query(self.request('model_evaluate')),'fixture',guard=Mock())
        h.store.reserve.assert_called_once()

    def test_unchanged_original_protocol_is_available_as_installed_resource(self):
        from tools.paths import resource_path
        name=self.full['supplied_evidence'][0]
        self.assertEqual(resource_path(name).read_bytes(),(self.directory.parents[1]/name).read_bytes())

    def test_explicit_owned_record_selection_composes_prior_calls_without_reexecution(self):
        request=self.request('subtract',sources=[REF,REF],source_record_indices=[0,1])
        source=dict(operation=direct_math.METHOD,candidate=REF,
            requested_operation={'direct_math':self.request('model_evaluate').model_dump(mode='json')},
            direct_math={'records':[{'observation':{'value':2.}},{'observation':{'value':5.}}]})
        context=self.prepare(request,[source,source])
        self.assertEqual(context['evaluations'],0)
        self.assertEqual([s['direct_math']['records'][0]['observation']['value'] for s in context['sources']],[2.,5.])
        invalid=self.request('subtract',sources=[REF],source_record_indices=[2])
        with self.assertRaisesRegex(ValueError,'OWNED_SOURCE_RECORD_INDEX_OUTSIDE_RESULT'):
            self.prepare(invalid,[source])

    def test_contrast_cannot_turn_missing_scalar_into_zero(self):
        from extensions.math_analysis.differentiation_router import interaction_evidence,matched_points
        points=matched_points([ROW,{**ROW,'parameter_id':'segments.1.length_m'}])
        records=[dict(record_index=i,parameter_values=p['parameter_values'],matching_identity='fixture',
            observation=dict(status='unavailable',value=None,unit='kg')) for i,p in enumerate(points)]
        value=interaction_evidence(points,records)
        self.assertEqual(value['status'],'incomplete');self.assertIsNone(value['interaction_effect'])

    def test_raw_array_arithmetic_uses_owned_observations_and_preserves_unknown(self):
        records=[dict(record_index=i,observation=dict(value=v,unit='N*m',status='computed')) for i,v in enumerate((2.,5.))]
        sources=[{'direct_math':{'records':[r]}} for r in records]
        factory=(Mock(side_effect=AssertionError('No model evaluation')),[],[],[],[],[])
        for function,expected in (('subtract',3.),('minimum',2.),('maximum',5.)):
            with patch.object(structure_research,'model_evaluator',return_value=factory):
                result=direct_math.calculate({}, {},self.query(self.request(function)),None,dict(sources=sources,selected_parameters=[]))
            self.assertEqual(result['direct_math']['result']['value'],expected)
        records[0]['observation']['value']=None
        with patch.object(structure_research,'model_evaluator',return_value=factory):
            result=direct_math.calculate({}, {},self.query(self.request('subtract')),None,dict(sources=sources,selected_parameters=[]))
        self.assertIsNone(result['direct_math']['result']['value'])

    def test_original_high_level_calculation_uses_shared_model_boundary(self):
        # This exercises the extracted Full path with synthetic data, including cost settlement.
        q=AnalysisRequest(candidate=REF,operation='mechanism_structure_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=self.full['analysis_protocol'],
            mechanism_study=dict(operation='inspect',target=dict(quantity='constraint_kkt_residual',goal='decrease'),point_semantics='re_equilibrated',load_condition='unloaded',max_evaluations=1))
        evaluate,records,models,failures,mappings,base=self.numerical_factory();original=evaluate
        def call(values=None,**kw):
            r=original(values);r['mechanics'].update(point_binding={},task_observations=[],qualification_diagnosis={});return r
        call.attempts=1
        with patch.object(structure_research,'model_evaluator',return_value=(call,records,models,failures,mappings,base)),patch('tools.research_tasks.task_adapter') as adapter,patch('extensions.math_analysis.differentiation_router.select_method',return_value={'method':'fixture'}):
            adapter.return_value.execution_requirements.return_value={'registered_acceptance':'fixture'}
            value=structure_research.calculate({'task':{'physical_problem':{'mode':'passive_unilateral_equilibrium'}}},{},q,{'actual_time_s':0.},{'selected_parameters':[]})
        self.assertEqual(value['structure_research']['cost']['evaluation_attempts'],1)
