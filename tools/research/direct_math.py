"""Thin, candidate-bound calls to existing numerical APIs; no research-intent compiler."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
from tools.platform_store import plain
from tools.research.contracts import DirectMathAPI,DirectMathToolRequest

METHOD='direct_math_api_v1'
APIS=('model_evaluate','stencil','matched_points','finite_difference','minimize',
      'interaction_evidence','observe','observed_task_improvement','subtract','minimum','maximum')


def enabled(spec):
    return bool(spec.get('mathematical_methods',{}).get(METHOD))


def schema(spec):
    value=DirectMathToolRequest.model_json_schema()
    value['properties']['function']['enum']=list(spec.get('direct_math_apis',APIS))
    return value


def prepare(spec,candidate,request,sources):
    from tools.research.structure_research import parameters,dynamic_cost
    from tools.research_tasks import task_adapter
    from extensions.math_analysis.mechanism_registry import PRIMITIVES
    from extensions.math_analysis.differentiation_router import stencil
    if not enabled(spec) or request.function not in spec.get('direct_math_apis',APIS):
        raise ValueError('DIRECT_MATH_API_NOT_AUTHORIZED')
    cfg=candidate['configuration'];parameters_value=candidate['parameters']
    if request.execution_profile:
        if request.effect_semantics!='finite_time_task_response':raise ValueError('PROFILE_REQUIRES_DYNAMIC_RESPONSE')
        from extensions.reference.passive_program import execution_scope
        from schemas.platform import TaskDefinition
        execution_scope(TaskDefinition.model_validate(cfg['task']),plain(request.execution_profile))
        if request.execution_profile.fidelity:
            from tools.research.design import fidelity_configuration
            cfg,parameters_value=fidelity_configuration(spec,candidate,request.execution_profile.fidelity)
    if request.passive_ablation:
        if request.effect_semantics!='finite_time_task_response' or not set(request.passive_ablation)<={t['id'] for t in cfg['robot']['structure']['data']['tendons']}:
            raise ValueError('DYNAMIC_INTERVENTION_REQUIRES_OWNED_TENDON_NAMES')
    problem=cfg['task'].get('physical_problem')
    if not problem or problem['mode']!='passive_unilateral_equilibrium':
        raise ValueError('DIRECT_V1_REQUIRES_PASSIVE_FROZEN_MODEL')
    capability=task_adapter(cfg).physical_capabilities()
    if capability['status']=='unsupported':raise ValueError('UNSUPPORTED_PHYSICAL_CAPABILITIES')
    pure=request.function in ('stencil','matched_points')
    if not pure and request.target is None:raise ValueError('EXPLICIT_REGISTERED_OBSERVABLE_REQUIRED')
    quantity=request.target.quantity if request.target is not None else None
    if not pure and (quantity not in PRIMITIVES or problem['mode'] not in PRIMITIVES[quantity]['physical_modes']):
        raise ValueError('OBSERVABLE_PHYSICAL_MODE_MISMATCH')
    dynamic=request.effect_semantics=='finite_time_task_response'
    if dynamic:
        if quantity!='finite_time_task_violation' or request.load_condition is not None or not capability['evaluation']['finite_time_structure_response']:
            raise ValueError('DYNAMIC_REQUIRES_COMPLETE_FROZEN_TASK_TARGET_AND_ALL_LOADS')
    elif not pure and request.load_condition not in [r['name'] for r in problem['loads']]:
        raise ValueError('FROZEN_LOAD_CONDITION_REQUIRED')
    if quantity=='re_equilibrated_position_response' and request.effect_semantics!='re_equilibrated_passive_response':raise ValueError('RELATIVE_POSITION_REQUIRES_RE_EQUILIBRATED_EFFECT')
    available={r['parameter_id']:r for r in parameters(spec,candidate,request.parameter_bounds)}
    if set(request.parameter_bounds)-set(request.parameter_paths):raise ValueError('BOUNDS_REQUIRE_SELECTED_PATHS')
    rows=[]
    for path in request.parameter_paths:
        row=available.get(path)
        if not row or not row['effective_in_current_execution']:raise ValueError('EFFECTIVE_REGISTERED_PARAMETER_REQUIRED')
        value=request.parameter_values.get(path,row['current_value'])
        if any(row.get(k) is None or not np.isfinite(row[k]) for k in ('minimum','maximum')):raise ValueError('FINITE_REGISTERED_LOCAL_BOUNDS_REQUIRED')
        if row.get('data_type')=='integer' and value!=int(value):raise ValueError('INTEGER_PARAMETER_VALUE_REQUIRED')
        if not row['minimum']<=value<=row['maximum']:raise ValueError('PARAMETER_OUTSIDE_FROZEN_DOMAIN')
        rows.append(row)
    fn=request.function
    operation={'finite_difference':'differentiate','minimize':'optimize','interaction_evidence':'interact'}.get(fn)
    if operation and operation not in PRIMITIVES[quantity]['operations']:raise ValueError('NUMERICAL_OPERATION_NOT_APPLICABLE_TO_OBSERVABLE')
    if fn in ('stencil','finite_difference') and len(rows)!=1:raise ValueError('ONE_CONTINUOUS_PARAMETER_REQUIRED')
    if fn in ('matched_points','interaction_evidence') and len(rows)!=2:raise ValueError('TWO_CONTINUOUS_PARAMETERS_REQUIRED')
    if fn=='minimize' and (not rows or any(not r['continuous_perturbation'] for r in rows)):
        raise ValueError('EXPLICIT_CONTINUOUS_PARAMETER_DOMAIN_REQUIRED')
    if fn in ('finite_difference','minimize') and PRIMITIVES[quantity]['shape'] and request.target.reduction=='identity':
        raise ValueError('SCALAR_OBSERVABLE_REQUIRED')
    if fn=='observed_task_improvement' and not dynamic:raise ValueError('FULL_TASK_RECORDS_REQUIRED')
    if fn=='interaction_evidence':
        if len(request.points)!=4 or {p.label for p in request.points}!={'00','10','01','11'}:
            raise ValueError('EXPLICIT_FOUR_DISTINCT_POINT_LABELS_REQUIRED')
        for point in request.points:
            if set(point.parameter_values)!=set(request.parameter_paths):raise ValueError('POINTS_REQUIRE_SELECTED_REGISTERED_PATHS')
            if any(not row['minimum']<=point.parameter_values[row['parameter_id']]<=row['maximum'] for row in rows):
                raise ValueError('POINT_OUTSIDE_FROZEN_DOMAIN')
    if fn=='model_evaluate':count=1
    elif fn=='finite_difference':count=1+len(set(stencil(rows[0])['coordinates']))
    elif fn=='minimize':count=request.max_evaluations
    else:count=0
    if count>request.max_evaluations:raise ValueError('EXPLICIT_EVALUATION_CAP_TOO_SMALL')
    if fn in ('finite_difference','minimize') and request.parameter_values:
        raise ValueError('SOLVER_CENTER_IS_OWNED_CANDIDATE_USE_MODEL_EVALUATE_FOR_EXPLICIT_POINTS')
    for value in sources:
        if value.get('operation')!=METHOD or request.function not in ('observe','observed_task_improvement','subtract','minimum','maximum') and value.get('candidate')!=plain(candidate.get('_reference')):
            raise ValueError('OWNED_SAME_CANDIDATE_DIRECT_RESULT_REQUIRED')
    for source in sources:
        if fn!='observe':
            original=source.get('requested_operation',{}).get('direct_math',{})
            for field in ('target','load_condition','effect_semantics','point_semantics','execution_profile','passive_ablation'):
                if not (fn in ('subtract','minimum','maximum') and field=='load_condition') and original.get(field)!=plain(request).get(field):raise ValueError('SAME_OBSERVABLE_AND_PHYSICAL_CONDITIONS_REQUIRED')
    if fn in ('observe','observed_task_improvement','interaction_evidence','subtract','minimum','maximum') and not sources:
        raise ValueError('OWNED_NUMERICAL_SOURCES_REQUIRED')
    if request.source_record_indices:
        selected=[]
        for source,index in zip(sources,request.source_record_indices):
            records=source.get('direct_math',{}).get('records',[])
            if index>=len(records):raise ValueError('OWNED_SOURCE_RECORD_INDEX_OUTSIDE_RESULT')
            selected.append({**source,'direct_math':{**source['direct_math'],'records':[records[index]]}})
        sources=selected
    return dict(space=spec['family_space'],parameters=parameters_value,execution_configuration=cfg,selected_parameters=rows,
        evaluations=count,match_parameters=True,sources=sources,
        dynamic_cost_bound=dynamic_cost(cfg,count,paired=bool(request.passive_ablation),profile=request.execution_profile) if dynamic and count else dict(episodes=0))


def options(request):
    # Model/state binding only: no MechanismStudy, semantic operation, automatic
    # diagnosis Plan, question compilation, parameter selection or research schedule.
    return SimpleNamespace(operation='model_evaluate',target=request.target,paths=request.parameter_paths,
        point_semantics=request.point_semantics,effect_semantics=request.effect_semantics,
        load_condition=request.load_condition,execution_profile=request.execution_profile,execution_checks='full',passive_ablation=request.passive_ablation)


def calculate(configuration,binding,query,point,context,*,checkpoint=None):
    from tools.research.structure_research import (model_evaluator,validate_sensitivity,
        observed_task_improvement,EvaluationLimit)
    from extensions.math_analysis import differentiation_router as router
    from extensions.math_analysis.mechanism_registry import observe
    request=query.direct_math;fn=request.function;study=options(request)
    low_query=SimpleNamespace(mechanism_study=study,native=query.native,candidate=query.candidate)
    evaluate,records,models,failures,mappings,base_values=model_evaluator(
        configuration,binding,low_query,point,context,checkpoint=checkpoint)
    rows=context['selected_parameters'];result=None
    saved=[deepcopy(record) for source in context['sources'] for record in source.get('direct_math',{}).get('records',[])]
    for i,record in enumerate(saved):record['record_index']=i
    if fn=='model_evaluate':
        result=evaluate([request.parameter_values.get(r['parameter_id'],r['current_value']) for r in rows])['observation']
    elif fn=='stencil':result=router.stencil(rows[0])
    elif fn=='matched_points':result=router.matched_points(rows)
    elif fn=='finite_difference':
        base=evaluate()
        if not finite_scalar(base['observation']):return result_envelope(fn,invalid_scalar(base),records,models,failures,binding,rows)
        result=router.differentiate(rows[0],base,lambda value:evaluate([value]),
            goal=request.target.goal,allow_ineligible=True)
        from tools.research_tasks import task_adapter
        selection=router.select_method(effect_semantics=study.effect_semantics,
            capabilities=task_adapter(configuration).physical_capabilities(),target=study.target.quantity)
        validate_sensitivity(rows[0],base,records,models,result,study,selection)
    elif fn=='minimize':
        from scipy.optimize import minimize
        base=evaluate()
        if not finite_scalar(base['observation']):return result_envelope(fn,invalid_scalar(base),records,models,failures,binding,rows)
        center=np.asarray([m['origin'] for m in mappings]);radius=request.local_radius_fraction
        bounds=[(max(0.,v-radius),min(1.,v+radius)) for v in center]
        preference=1 if request.target.goal=='increase' else -1
        def objective(z):
            observation=evaluate([router.physical_value(m,float(v)) for m,v in zip(mappings,z)])['observation']
            value=observation['value']
            return -preference*float(value) if value is not None and np.asarray(value).ndim==0 else float('inf')
        try:
            solved=minimize(objective,center,method='Powell',bounds=bounds,
                options=dict(maxfev=request.max_evaluations,maxiter=16,xtol=1e-4,ftol=1e-8))
            result=dict(method='scipy.optimize.minimize/Powell',success=bool(solved.success),
                status=int(solved.status),message=str(solved.message),function_calls=int(solved.nfev),
                x_normalized=list(map(float,solved.x)),bounds_normalized=bounds)
        except EvaluationLimit:result=dict(method='scipy.optimize.minimize/Powell',status='evaluation_cap',success=False)
        result['task_improvement']=observed_task_improvement(records) if request.effect_semantics=='finite_time_task_response' else dict(status='unmeasured',reason='Static observable optimization is not task improvement.')
        result.update(strict_derivative=False,descent_certificate=False,task_acceptance='unmeasured')
    elif fn=='observe':result=[observe(r['mechanics'],request.target) for r in saved]
    elif fn=='observed_task_improvement':result=observed_task_improvement(saved)
    elif fn in ('subtract','minimum','maximum'):
        observations=[r['observation'] for r in saved]
        units={r.get('unit') for r in observations}
        if len(units)!=1 or None in units:raise ValueError('KNOWN_MATCHED_OBSERVABLE_UNITS_REQUIRED')
        if fn=='subtract' and len(observations)!=2:raise ValueError('SUBTRACTION_REQUIRES_TWO_OWNED_RECORDS')
        values=[r.get('value') for r in observations]
        valid=all(r.get('status')=='computed' and v is not None and np.isfinite(v).all() for r,v in zip(observations,values))
        if not valid:result=dict(status='not_comparable',value=None,unit=next(iter(units)))
        else:
            arrays=[np.asarray(v) for v in values]
            if len({v.shape for v in arrays})!=1:raise ValueError('MATCHED_OBSERVABLE_SHAPES_REQUIRED')
            value=(arrays[1]-arrays[0] if fn=='subtract' else np.minimum.reduce(arrays) if fn=='minimum' else np.maximum.reduce(arrays))
            result=dict(status='computed',value=value.tolist(),unit=next(iter(units)),
                scope='Arithmetic on explicitly selected owned observations; physical matching and causality are not inferred.')
    elif fn=='interaction_evidence':
        if len(request.points)!=4:raise ValueError('EXPLICIT_FOUR_POINT_DESIGN_REQUIRED')
        # Matching identities, units, state qualification and missing observations
        # are checked by the same kernel used by Structured interact.
        result=router.interaction_evidence([plain(p) for p in request.points],saved)
    return result_envelope(fn,result,records,models,failures,binding,rows)


def finite_scalar(observation):
    value=observation.get('value')
    return value is not None and np.asarray(value).ndim==0 and bool(np.isfinite(value))


def invalid_scalar(record):
    return dict(status='not_comparable',derivative_status='not_defined',reason='NO_VALID_FINITE_SCALAR_BASELINE',
        observation=record['observation'],strict_derivative=False,descent_certificate=False)


def result_envelope(fn,result,records,models,failures,binding,rows):
    costs={}
    for model in models:
        for key,value in model.cost.items():costs[key]=costs.get(key,0)+value
    return dict(status='computed',operation=METHOD,binding=binding,task_acceptance='unmeasured',
        direct_math=dict(function=fn,result=plain(result),records=records,cost=costs,failures=failures,parameter_metadata=plain(rows),
            scope='Frozen candidate-bound numerical API result; no high-level research operation or task acceptance.'),
        internal_calculations=[dict(purpose=fn,**costs)])


def dispatch(host,payload,key,*,guard):
    from tools.research.state import state
    from tools.research.analysis import dispatch as execute
    from tools.research.config import frozen_analysis_protocol
    from tools.research.design import verify_candidate
    from tools.research.contracts import AnalysisRequest
    request=DirectMathToolRequest.model_validate(payload)
    spec=state(host)['spec']
    if not enabled(spec) or request.function not in spec.get('direct_math_apis',APIS):raise ValueError('DIRECT_MATH_API_NOT_AUTHORIZED')
    candidate=verify_candidate(host,request.candidate)
    api=DirectMathAPI.model_validate({k:v for k,v in plain(request).items() if k!='candidate'})
    query=AnalysisRequest(candidate=request.candidate,operation=METHOD,model_source='mujoco',
        operating_point='standardized_initial_pretension',direct_math=api,
        protocol=frozen_analysis_protocol(spec,candidate))
    return execute(host,query,key,guard=guard)
