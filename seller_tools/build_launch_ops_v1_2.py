from __future__ import annotations
import hashlib, json, subprocess, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'launch_ops'/'v1.2'
NAME='CK-NEXUS-Launch-Operations-v1.2'
BASE='45fde79c717b09f8675645aa541a5834ebd4f433'
EXPECTED='51718986a19e6d11467a9e9e9ab536392b38c59cd674a5f1a7a656632b4011fe'
PATHS=['creator_app','services','tests','scripts','main.py','pyproject.toml','uv.lock']
def run(*a): return subprocess.run(a,cwd=ROOT,text=True,capture_output=True,check=False)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def subject():
 p=run('git','ls-tree','-r','HEAD','--',*PATHS)
 if p.returncode: raise RuntimeError(p.stderr)
 return hashlib.sha256(p.stdout.encode()).hexdigest()
def main():
 dirty=run('git','status','--porcelain')
 if dirty.stdout.strip(): raise RuntimeError('dirty tree')
 head=run('git','rev-parse','HEAD').stdout.strip()
 if run('git','merge-base','--is-ancestor',BASE,head).returncode: raise RuntimeError('invalid lineage')
 s=subject()
 if s!=EXPECTED: raise RuntimeError(f'runtime subject drift: {s}')
 out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT.parent/'launch-ops-build'; out.mkdir(parents=True,exist_ok=True)
 z=out/f'{NAME}.zip'
 info=json.dumps({'schema_version':1,'package':NAME,'head_sha':head,'runtime_base':BASE,'runtime_subject_sha256':s,'classification':'INTERNAL_SELLER_OPS','production_ready':False},indent=2)+'\n'
 files=[]
 with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as a:
  for p in sorted(SRC.rglob('*')):
   if p.is_file():
    arc=f'{NAME}/{p.relative_to(SRC).as_posix()}'; a.write(p,arc); files.append((sha(p),arc))
  a.writestr(f'{NAME}/BUILD_INFO.json',info)
  sums=''.join(f'{d}  {n}\n' for d,n in files)
  a.writestr(f'{NAME}/SHA256SUMS.txt',sums)
 d=sha(z); z.with_suffix('.zip.sha256').write_text(f'{d}  {z.name}\n')
 print(z); print(d)
if __name__=='__main__': main()
