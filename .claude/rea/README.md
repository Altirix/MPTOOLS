# REA project `mptools`

Vendor MP-tool archives from this repo, served to REA (Ghidra, rizin, objdump) on its VM. Adapted from
`Altirix/REA-IG5236` `.claude/rea/`; the analysis notes live in the `Altirix/REA-<controller>` repos.

| What | Where |
|---|---|
| REA project | `mptools` |
| MCP endpoint | `https://mcp.peacocks.me/rea/mptools/mcp` (`rea`: everything, Ghidra included) |
| CLI endpoint | `https://mcp.peacocks.me/rea/mptools/cli/mcp` (`rea-cli`: rizin, objdump, firmware, process tools) |
| Samples (HTTP) | `https://mcp.peacocks.me/rea/mptools/samples/<name>` (PUT / GET / DELETE, no subdirectories, ≤ 1 GB) |
| Samples (VM) | `/var/lib/rea/mptools/samples/<name>` |
| Evidence (HTTP) | `https://mcp.peacocks.me/rea/mptools/shared/evidence/` (GET) |
| Scratch (VM) | `/var/lib/rea/mptools/scratch/<agent>/` |

The agent proxy adds auth: send no Authorization header. `.mcp.json` registers both endpoints.

## Samples

Every file in the repo (except `README.md`, `.mcp.json`, `.claude/`) is a sample. Its name is the repo path with `/`
replaced by `__`, e.g. `IG5216__ShastaPlus_FTK_1.T.V.2Y_MP_2.0.0.13_RDT_2.K.0.1_package.7z`. `samples.tsv` lists
name, sha256, size and repo path.

Run these from a full checkout:

```bash
python3 .claude/rea/sync_samples.py --check
```

```bash
python3 .claude/rea/sync_samples.py --upload
```

```bash
python3 .claude/rea/sync_samples.py --regen
```

- `--check` compares the checkout with the manifest, offline.
- `--upload` PUTs the manifest files missing from the REA listing; add `--all` to re-send everything.
- `--regen` rewrites `samples.tsv` after files are added or changed. Commit it with the files.

Names with `[` `]` need `curl -g`, which the script passes.

## Archives

Most samples are `.7z` archives. For a firmware inside one:
- extract it on the VM (REA `extract_artifact` into scratch), or
- extract it locally and upload the file as `<archive name>__<file>` (e.g.
  `IG5216__ShastaPlus…package.7z__ftkdisk_mu_hmb.fw`). Record its sha256 in the REA-<controller> notes.

Uploads of derived files (ELFs, extracted images) are not in `samples.tsv`; name them `<branch>__<name>` so they don't
replace a repo sample.

## Calling REA without an MCP client

`rea_call.py` speaks MCP over plain HTTP. Set `REA_SESSION=<file>` to keep one REA session (and Ghidra's analysis)
across calls. Each new session pays Ghidra's first-query analysis.

```bash
python3 .claude/rea/rea_call.py --list
```

```bash
REA_SESSION=.rea_session python3 .claude/rea/rea_call.py open_binary '{"path":"/var/lib/rea/mptools/samples/<name>"}'
```
