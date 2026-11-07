#!/usr/bin/env python3
"""sync_samples.py -- keep REA project `mptools` samples in step with this repo.

  python3 .claude/rea/sync_samples.py --regen   rewrite samples.tsv from the checkout
  python3 .claude/rea/sync_samples.py --check   checkout vs samples.tsv (sha256), no network
  python3 .claude/rea/sync_samples.py --upload  PUT every manifest file missing from the
                                                REA samples listing (--all: PUT every file)

Sample name = repo path with '/' replaced by '__' (REA samples have no subdirectories).
Needs a full checkout (the files, not LFS stubs). The agent proxy adds auth.
"""
import hashlib, os, subprocess, sys, urllib.parse, urllib.request, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MAN = os.path.join(HERE, "samples.tsv")
BASE = "https://mcp.peacocks.me/rea/mptools/samples/"
SKIP_TOP = {".git", ".claude"}
SKIP_FILES = {".mcp.json", "README.md"}

def repo_files():
    out = []
    for d, dn, fn in os.walk(ROOT):
        rel = os.path.relpath(d, ROOT)
        top = rel.split(os.sep)[0]
        if top in SKIP_TOP:
            dn[:] = []
            continue
        for f in fn:
            r = os.path.normpath(os.path.join(rel, f)).replace(os.sep, "/")
            if r in SKIP_FILES:
                continue
            out.append(r)
    return sorted(out)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def name_of(r):
    return r.replace("/", "__")

def read_man():
    rows = []
    for line in open(MAN, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        n, s, size, r = line.rstrip("\n").split("\t")
        rows.append((n, s, int(size), r))
    return rows

def regen():
    rows = [(name_of(r), sha(os.path.join(ROOT, r)), os.path.getsize(os.path.join(ROOT, r)), r) for r in repo_files()]
    names = [n for n, *_ in rows]
    if len(set(names)) != len(names):
        sys.exit("name collision after '/' -> '__'")
    with open(MAN, "w", encoding="utf-8") as f:
        f.write("# REA `mptools` sample manifest (generated: sync_samples.py --regen)\n")
        f.write("# name\tsha256\tbytes\trepo path\n")
        for row in rows:
            f.write("%s\t%s\t%d\t%s\n" % row)
    print("wrote %d rows" % len(rows))

def check():
    man = {r: s for n, s, size, r in read_man()}
    files = set(repo_files())
    missing = sorted(set(man) - files)
    extra = sorted(files - set(man))
    bad = [r for r in sorted(files & set(man)) if sha(os.path.join(ROOT, r)) != man[r]]
    print("manifest %d, checkout %d, missing %d, unlisted %d, sha mismatch %d"
          % (len(man), len(files), len(missing), len(extra), len(bad)))
    for tag, lst in (("missing", missing), ("unlisted", extra), ("mismatch", bad)):
        for r in lst[:5]:
            print("  %s %s" % (tag, r))
    return 1 if (missing or extra or bad) else 0

def listing():
    html = urllib.request.urlopen(BASE).read().decode("utf-8", "replace")
    return {urllib.parse.unquote(h) for h in re.findall(r'href="([^"]+)"', html) if h != "../"}

def upload(all_):
    have = set() if all_ else listing()
    todo = [(n, r) for n, s, size, r in read_man() if n not in have]
    ok = fail = 0
    for n, r in todo:
        cmd = ["curl", "-g", "-fsS", "-T", os.path.join(ROOT, r), BASE + urllib.parse.quote(n), "-o", "/dev/null"]
        for _ in range(3):
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                break
        if res.returncode == 0:
            ok += 1
        else:
            fail += 1
            print("FAIL %s: %s" % (n, res.stderr.strip()[:160]))
    print("uploaded %d, failed %d, already present %d" % (ok, fail, len(read_man()) - len(todo)))
    return 1 if fail else 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--regen"]:
        regen()
    elif a[:1] == ["--check"]:
        sys.exit(check())
    elif a[:1] == ["--upload"]:
        sys.exit(upload("--all" in a))
    else:
        sys.exit(__doc__)
