"""Unified research composition entrypoint."""
from tools.paths import RUNS
import argparse,asyncio,json
from pathlib import Path
from uuid import uuid4
from tools.paths import resource_path,data_path
DEFAULT_SPEC=resource_path('examples/study-reach.json')
from tools.research.state import state
from tools.platform_host import Host
from tools.state_io import read

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['examples','registry','validate','init-store','models','environment','readiness','run','prepare','bind','migrate','execute','rl','diagnose','recover','status','export'])
    parser.add_argument('--runtime',type=Path,help='Explicit model-directory operation; contacts the configured Provider only when models is requested')
    parser.add_argument('--spec',type=Path,default=DEFAULT_SPEC)
    parser.add_argument('--example',choices=['reach','tracking'],help='Use a bundled generic example')
    parser.add_argument('--store',type=Path,help='Explicit Store directory; defaults below SOFTROBOT_AGENT_HOME')
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--run-id')
    parser.add_argument('--profile')
    parser.add_argument('--request-id')
    parser.add_argument('--reason')
    parser.add_argument('--session-handoff',action=argparse.BooleanOptionalAction,default=None,
        help='Override automatic frozen conversation-policy handoff; still requires separate live continuation admission')
    parser.add_argument('--restore-only',action='store_true',help='Reopen and verify original SDK/Store recovery without a new Provider request')
    parser.add_argument('--delivery-only',action='store_true',help='Main delivers a final answer from existing evidence, then pauses; no further experiments or Reporter calls')
    parser.add_argument('--recover-incomplete',action='store_true',help='Dispose a verified settled truncated response via an audited clean-session boundary')
    parser.add_argument('--max-new-provider-requests',type=int,help='Pause after this many new requests including Reporter calls')
    parser.add_argument('--handoff-before-next-request',action='store_true',help='Use independently admitted request-feedback boundary before the next model send')
    parser.add_argument('--handoff-request-bytes',type=int,help='Rotate at a verified paired-feedback boundary when the complete next request reaches this size; requires separate live admission')
    parser.add_argument('--pause-exploration-remaining',type=int,help='Supervisor pause at admitted paired-feedback boundary before remaining science-capable main requests reach this count')
    parser.add_argument('--pause-after-completed-invocations',type=int,help='Supervisor pause after complete SDK invocation and Reporter delivery')
    args=parser.parse_args()
    if args.example:args.spec=resource_path('examples/study-'+args.example+'.json')
    if args.command=='examples':
        print(json.dumps({name:str(resource_path('examples/study-'+name+'.json')) for name in ('reach','tracking')}))
        return
    if args.command=='registry':
        from tools.platform_registry import registry
        print(json.dumps(registry().catalog()))
        return
    if args.command=='validate':
        from tools.research.config import resolve
        from tools.platform_tasks import check_definition
        spec=resolve(args.spec)
        task=check_definition(spec['configuration']['task'])
        print(json.dumps(dict(valid=True,study_id=spec['study_id'],task_id=task.task_id,
            task_family=task.family,provider_requests_sent=0,physics_steps=0)))
        return
    if args.command=='init-store':
        from tools.platform_store import Store
        from schemas.platform import ProjectConfig
        run_id=args.run_id or 'local-project'
        store=Store(args.store or RUNS/'research'/run_id)
        config=ProjectConfig(project_id=run_id,grant_id=run_id+'-'+uuid4().hex,
            authorization_source='Local operator initialized an empty Store; no research execution authorized.',
            budget=dict(model_calls=0,backend_solves=0,tool_calls=0,worker_calls=0,wall_s=0.))
        store.create(config)
        print(json.dumps(dict(store=str(store.db),initialized=True,sessions=0,provider_requests_sent=0)))
        return
    from tools.research.core import prepare,bind,dispatch,diagnose,recover,export,packet
    if args.command=='models':
        if args.runtime is None:parser.error('models requires an explicit --runtime; no Study is created')
        from tools.research.provider import credential,discover_models
        runtime=read(args.runtime)
        print(json.dumps(asyncio.run(discover_models(runtime['provider'],credential(runtime['provider'],data_path(runtime['credentials_reference']))))))
        return
    if args.command=='environment':
        from tools.research.config import resolve
        from tools.research.tool_readiness import execution_environment
        print(json.dumps(execution_environment(resolve(args.spec))))
        return
    if args.command in ('prepare','readiness'):
        h=prepare(args.spec,directory=args.store,profile=args.profile)
    else:
        if not args.run_id:
            parser.error('existing-study commands require --run-id; editable sources are not loaded')
        h=Host(args.store or RUNS/'research'/args.run_id,args.run_id,actor='unified-research')
        state(h)  # Require an existing frozen session, without source resolution.
    spec=state(h)['spec']
    if args.command=='readiness':
        from tools.research.tool_readiness import check
        print(json.dumps(check(h)))
        return
    if args.command in ('bind','migrate'):
        bind(h,args.reason if args.command=='migrate' else None,spec)
    elif args.command=='rl':
        from tools.research.rl import dispatch as rl_dispatch
        print(json.dumps(rl_dispatch(h,read(args.plan),args.request_id or 'manual-'+uuid4().hex)))
        return
    elif args.command=='execute':
        print(json.dumps(dispatch(h,read(args.plan),args.request_id or 'manual-'+uuid4().hex,origin='engineering')))
        return
    elif args.command=='diagnose':
        print(json.dumps(diagnose(h,state(h)['results'])))
        return
    elif args.command=='recover':
        print(json.dumps(recover(h)))
        return
    elif args.command=='run':
        from tools.research.agent import converse,IncompleteModelOutput
        try:asyncio.run(converse(h,session_handoff=args.session_handoff,
            pause_after_completed_invocations=args.pause_after_completed_invocations,
            handoff_before_next_request=args.handoff_before_next_request,handoff_request_bytes=args.handoff_request_bytes,
            pause_exploration_remaining=args.pause_exploration_remaining,restore_only=args.restore_only,recover_incomplete=args.recover_incomplete,max_new_provider_requests=args.max_new_provider_requests,delivery_only=args.delivery_only))
        except IncompleteModelOutput as exc:
            print(json.dumps(dict(status='confirmed_incomplete',provider=exc.diagnostic)))
            raise SystemExit(2) from exc
    elif args.command=='export':
        print(json.dumps(export(h)))
        return
    print(json.dumps(packet(h)))

if __name__=='__main__':
    main()
