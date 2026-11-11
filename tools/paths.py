"""Installed code resources and user-owned runtime data."""
import hashlib
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
ASSETS=Path(__file__).resolve().parent/'assets'
DATA_HOME=Path(os.environ.get('SOFTROBOT_AGENT_HOME',str(Path.home()/'.softrobot-agent'))).expanduser().resolve()
RUNS=DATA_HOME/'runs'


def resource_path(relative):
    source=ROOT/relative
    return source if source.is_file() or source.is_dir() else ASSETS/relative


def data_path(path):
    path=Path(path).expanduser()
    return path if path.is_absolute() else DATA_HOME/path


def implementation_status():
    """Git identity for a checkout; installed source digest for a wheel."""
    if (ROOT/'.git').exists():
        commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
        if commit.returncode==0:
            dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
            return dict(project_commit=commit.stdout.strip(),worktree_dirty=bool(dirty))
    digest=hashlib.sha256()
    for package in ('tools','schemas','extensions'):
        for path in sorted((ROOT/package).rglob('*')):
            if path.is_file() and path.suffix in ('.py','.json','.m'):
                digest.update(path.relative_to(ROOT).as_posix().encode())
                digest.update(path.read_bytes())
    return dict(project_commit=digest.hexdigest(),worktree_dirty=False)
