"""
Extract `ensures` clauses from DafnyBench's ground-truth programs

Usage:  python3 extract_dafnybench.py <DafnyBench/test.json from https://github.com/sun-wendy/DafnyBench>
Writes: dafnybench_ensures.json  (test_file, postcondition)
"""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sm_dafny import HARNESS, find_dotnet

programs = json.load(open(sys.argv[1]))
tmp = tempfile.mkdtemp()
paths = []
for p in programs:                           
    path = os.path.join(tmp, p['test_file'])
    open(path, 'w').write(p['ground_truth'])
    paths.append(path)

dotnet = find_dotnet()
env = dict(os.environ, DOTNET_ROOT=os.path.dirname(os.path.realpath(dotnet)), DOTNET_CLI_TELEMETRY_OPTOUT='1')
out = subprocess.run([dotnet, HARNESS] + paths, capture_output=True, text=True, check=True, env=env)
rows, failed = [], 0
for p, line in zip(programs, out.stdout.splitlines()):
    r = json.loads(line)
    failed += r['errors'] > 0
    rows += [{'test_file': p['test_file'], 'postcondition': ' '.join(e.split())} for e in r['ensures']]
json.dump(rows, open(os.path.join(HERE, 'dafnybench_ensures.json'), 'w'), indent=0)
print(f'{len(programs)} programs ({failed} failed to parse), {len(rows)} ensures clauses')
