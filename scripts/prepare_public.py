"""Build-time configuration; no secrets are written to public files."""
import json,os,pathlib,re,shutil
root=pathlib.Path(__file__).resolve().parents[1]
repo=os.environ.get('GITHUB_REPOSITORY','')
if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise SystemExit('GITHUB_REPOSITORY must be owner/repository')
(root/'dist/config.json').write_text(json.dumps({'repository':repo,'refreshWorkflow':'refresh.yml','deployment':'github-pages'},indent=2))
(root/'dist/.nojekyll').touch()
# Sites metadata must never be part of an exported public build.
if (root/'dist/.openai').exists():shutil.rmtree(root/'dist/.openai')
print('Public app configured for '+repo)
