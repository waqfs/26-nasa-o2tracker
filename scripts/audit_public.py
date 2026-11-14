"""Review the complete publication tree and local Git history without publishing."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IGNORED={'.git','.venv','__pycache__','.pytest_cache','outputs','node_modules','dist'}
FORBIDDEN={'internal','research','experiments','ai-notes','tools','raw'}
PERSONAL=re.compile(r'[A-Za-z]:[\\/]Users[\\/]|' + r'/ho' + r'me/[^/\s]+/|' + r'/Us' + r'ers/[^/\s]+/')
SECRET=re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
SIGNED=re.compile(r'X-Amz-' + r'Signature=|[?&]sig=[A-Za-z0-9%+/]{20,}',re.I)

def excluded(path):
    return any(part in IGNORED or part.endswith('.egg-info') for part in path.parts)

def inspect_text(text):
    found=[]
    if PERSONAL.search(text):found.append('personal absolute path')
    if SECRET.search(text):found.append('credential-like value')
    if SIGNED.search(text):found.append('signed credential URL')
    return found

def main():
    findings=[];records=[]
    for path in ROOT.rglob('*'):
        relative=path.relative_to(ROOT)
        if excluded(relative) or not path.is_file():continue
        if FORBIDDEN & set(relative.parts):findings.append(dict(path=relative.as_posix(),issue='internal/raw directory'))
        size=path.stat().st_size
        if size>25*1024*1024:findings.append(dict(path=relative.as_posix(),issue='file exceeds 25 MiB'))
        data=path.read_bytes()
        if path.suffix not in ['.png','.jpg','.mp4','.npz']:
            try:
                for issue in inspect_text(data.decode('utf-8-sig')):findings.append(dict(path=relative.as_posix(),issue=issue))
            except UnicodeDecodeError:findings.append(dict(path=relative.as_posix(),issue='unexpected non-UTF8 text'))
        if relative.as_posix()!='data/derived/public_audit.json':
            records.append(dict(path=relative.as_posix(),bytes=size,sha256=hashlib.sha256(data).hexdigest()))
    history=subprocess.run(['git','rev-list','--objects','--all'],cwd=ROOT,capture_output=True,text=True,check=True)
    for line in history.stdout.splitlines():
        oid,_,name=line.partition(' ')
        kind=subprocess.run(['git','cat-file','-t',oid],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
        if kind!='blob':continue
        data=subprocess.run(['git','cat-file','blob',oid],cwd=ROOT,capture_output=True,check=True).stdout
        try:issues=inspect_text(data.decode('utf-8-sig'))
        except UnicodeDecodeError:continue
        for issue in issues:findings.append(dict(path=name,history_blob=oid,issue=issue))
    remote=subprocess.run(['git','remote','-v'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    result=dict(status='PASS' if not findings else 'REVIEW REQUIRED',findings=findings,files=records,
                public_root='public-repo',remote_configured=bool(remote),published=False,
                license='MIT for project code; source-specific rights in DATA_SOURCES.md',
                scope='Automated pattern/size/boundary/history scan. It complements human review and does not certify all secrets or licensing.')
    (ROOT/'data/derived/public_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=result['status'],file_count=len(records),findings=findings,remote_configured=bool(remote))))
    if findings:raise SystemExit(1)

if __name__=='__main__':main()
