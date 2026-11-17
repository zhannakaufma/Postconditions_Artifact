"""
Extract `ensures` clauses from OpenJML's JML specifications of the Java
standard library using jmlparser. 

Usage:  python3 extract_openjml_jdk.py <clone of https://github.com/OpenJML/Specs>
Writes: openjml_jdk_ensures.json  (file, postcondition)
"""
import glob, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from sm_jml import JAR, HARNESS
from libs.shevrin_maoz_metrics import find_java

root = sys.argv[1]
files = sorted(glob.glob(os.path.join(root, 'specs', '**', '*.jml'), recursive=True))
out = subprocess.run([find_java(), '-cp', f'{JAR}{os.pathsep}{HARNESS}', 'SMJml'] + files,
                     capture_output=True, text=True, check=True)
rows, problems = [], 0
for line in out.stdout.splitlines():
    r = json.loads(line)
    problems += r['problems']
    rows += [{'file': os.path.relpath(r['file'], root), 'postcondition': e} for e in r['ensures']]
json.dump(rows, open(os.path.join(HERE, 'openjml_jdk_ensures.json'), 'w'), indent=0)
print(f'{len(files)} files ({problems} parse problems reported by jmlparser), {len(rows)} ensures clauses')
