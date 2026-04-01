# CAD Agent

**Give your AI agent eyes for CAD — with local, native CLI execution.**

CAD Agent is now a **CLI-first tool** driven exclusively through `./cad.sh`.  
No HTTP server. No MCP transport. No agent-managed container orchestration.

---

## Why this exists

AI agents can generate CAD code, but they need visual and geometric feedback to iterate reliably.

CAD Agent provides that feedback loop locally:

1. Execute `build123d` code from a file
2. Render PNG previews
3. Measure geometry
4. Export STL/STEP/3MF

All through one stable command surface: `cad.sh`.

---

## Command surface (single gateway)

Use **only**:

- `./cad.sh setup`
- `./cad.sh doctor`
- `./cad.sh build ...`
- `./cad.sh render ...`
- `./cad.sh measure ...`
- `./cad.sh export ...`
- `./cad.sh all ...`
- `./cad.sh cli ...`

---

## Quick start

### 1) Setup environment

```bash
./cad.sh setup
./cad.sh doctor
```

`setup` creates `.env` and installs dependencies.  
`doctor` verifies Python + required packages.

### 2) Create a CAD code file

Create `workspace/part.py`:

```python
from build123d import *

base = Box(80, 40, 10)
hole1 = Cylinder(4, 12).locate(Pos(-25, 0, 0))
hole2 = Cylinder(4, 12).locate(Pos(25, 0, 0))

# Final shape must be assigned to `result`
result = base - hole1 - hole2
```

### 3) Build

```bash
./cad.sh build --code-file workspace/part.py --name part
```

### 4) Render preview

```bash
./cad.sh render \
  --code-file workspace/part.py \
  --name part \
  --mode 3d \
  --view iso \
  --output renders/part_iso.png
```

### 5) Export manufacturing files

```bash
./cad.sh export \
  --code-file workspace/part.py \
  --name part \
  --format stl \
  --output exports/part.stl

./cad.sh export \
  --code-file workspace/part.py \
  --name part \
  --format step \
  --output exports/part.step
```

---

## Entrypoint commands

### `setup`
Create local venv and install dependencies.

```bash
./cad.sh setup
```

### `doctor`
Validate runtime readiness.

```bash
./cad.sh doctor
```

### `build`
Execute CAD file and return build result JSON.

```bash
./cad.sh build --code-file workspace/part.py --name part
```

### `render`
Build + render image.

Supported modes:
- `3d`
- `2d`
- `multiview`
- `blueprint`

Examples:

```bash
./cad.sh render --code-file workspace/part.py --name part --mode 3d --view iso --output renders/part_iso.png
./cad.sh render --code-file workspace/part.py --name part --mode 2d --view front --output renders/part_front.png
./cad.sh render --code-file workspace/part.py --name part --mode multiview --output renders/part_multi.png
./cad.sh render --code-file workspace/part.py --name part --mode blueprint --views front,right,top,bottom --title "PART REV A" --output renders/part_blueprint.png
```

### `measure`
Build + print dimensions/geometry summary.

```bash
./cad.sh measure --code-file workspace/part.py --name part
```

### `export`
Build + export one format (`stl`, `step`, `3mf`).

```bash
./cad.sh export --code-file workspace/part.py --name part --format stl --output exports/part.stl
```

### `all`
One-shot pipeline: render + measure + STL + STEP.

```bash
./cad.sh all \
  --code-file workspace/part.py \
  --name part \
  --view iso \
  --render renders/part_iso.png \
  --stl exports/part.stl \
  --step exports/part.step
```

### `cli`
Raw passthrough to underlying CLI.

```bash
./cad.sh cli --help
```

---

## File contract for `--code-file`

Your Python file must:

1. be valid Python
2. use `build123d`
3. assign the final geometry to `result`

If `result` is missing, build may succeed but geometry operations can fail or be ambiguous.

---

## Agent workflow recommendation

1. Write/modify `workspace/<model>.py`
2. `build`
3. `render` (usually `3d` + `multiview`)
4. inspect output image
5. `measure` for constraints
6. `export` when approved

---

## Output conventions

- Renders: `renders/`
- CAD exports: `exports/` (or `workspace/` if no explicit output provided)
- CLI output: JSON (agent-parseable)

---

## Troubleshooting

- **No output image appears**
  - Re-run with explicit output:
    - `--output renders/<name>.png`
  - Check command exit code and JSON error output.
- **Build failed**
  - Verify Python syntax and `build123d` usage.
- **Render is blank**
  - Use `--mode 3d --view iso` first; renderer includes fallback backends.
- **Dependency issues**
  - Re-run:
    - `./cad.sh setup`
    - `./cad.sh doctor`

---

## Security & design file hygiene

This repo is configured to avoid accidental design-file commits:

- `.gitignore` excludes CAD artifacts (`*.stl`, `*.step`, `*.3mf`, etc.)
- output folders are local and intended to stay unversioned
- optional pre-commit hook can block CAD artifacts

Enable hooks:

```bash
git config core.hooksPath .githooks
```

