# CAD Agent (CLI Skill)

> Native, local CAD execution for agents using command-line workflows.  
> No HTTP server, no MCP transport, no Docker orchestration.

## What this is

`cad-agent` is now CLI-first.  
You run commands against an executable Python CAD file (`--code-file`) and get JSON output plus generated artifacts.

Primary workflows:

1. **build** — execute build123d code
2. **render** — generate PNG views
3. **export** — write STL/STEP/3MF files
4. **measure** — return dimensions/geometry stats

---

## Install

Always use a local virtual environment:

~~~bash
python3 -m venv .env
source .env/bin/activate
.env/bin/python -m pip install --upgrade pip
.env/bin/python -m pip install -r requirements.txt
~~~

---

## CAD code file contract

Your `--code-file` must contain valid Python using `build123d` and assign final geometry to `result`.

Example (`workspace/bracket.py`):

~~~python
from build123d import *

result = Box(60, 40, 10) - Cylinder(5, 10).locate(Pos(20, 0, 0))
~~~

---

## CLI overview

Show help:

~~~bash
.env/bin/python -m src.cli --help
~~~

All commands support shared flags:

- `--workspace` (default: `workspace`)
- `--render-dir` (default: `renders`)
- `--code-file` (required on subcommands)
- `--name` (default: `default`)

---

## 1) Build

Execute CAD code and report build status.

~~~bash
.env/bin/python -m src.cli build \
  --code-file workspace/bracket.py \
  --name bracket
~~~

Returns JSON including `success`, `error` (if any), and geometry metadata.

Use this when you want to validate code before rendering/exporting.

---

## 2) Render

Build model and produce image output.

### 3D render (iso)

~~~bash
.env/bin/python -m src.cli render \
  --code-file workspace/bracket.py \
  --name bracket \
  --mode 3d \
  --view iso \
  --output renders/bracket_iso.png
~~~

### 2D orthographic render

~~~bash
.env/bin/python -m src.cli render \
  --code-file workspace/bracket.py \
  --name bracket \
  --mode 2d \
  --view front \
  --output renders/bracket_front.png
~~~

Optional toggles for `--mode 2d`:

- `--no-dimensions`
- `--no-hidden`

### Multiview render

~~~bash
.env/bin/python -m src.cli render \
  --code-file workspace/bracket.py \
  --name bracket \
  --mode multiview \
  --output renders/bracket_multiview.png
~~~

### Blueprint render

~~~bash
.env/bin/python -m src.cli render \
  --code-file workspace/bracket.py \
  --name bracket \
  --mode blueprint \
  --views front,right,top,bottom \
  --title "BRACKET REV A" \
  --specs "MATERIAL: PLA\nTOLERANCE: ±0.2mm" \
  --output renders/bracket_blueprint.png
~~~

---

## 3) Export (STL/STEP/3MF)

Build model and export manufacturing/CAD files.

### STL

~~~bash
.env/bin/python -m src.cli export \
  --code-file workspace/bracket.py \
  --name bracket \
  --format stl \
  --output exports/bracket.stl
~~~

### STEP

~~~bash
.env/bin/python -m src.cli export \
  --code-file workspace/bracket.py \
  --name bracket \
  --format step \
  --output exports/bracket.step
~~~

### 3MF

~~~bash
.env/bin/python -m src.cli export \
  --code-file workspace/bracket.py \
  --name bracket \
  --format 3mf \
  --output exports/bracket.3mf
~~~

If `--output` is a directory, the CLI auto-generates a file name.

---

## 4) Measure

Build model and print dimensions + geometry stats.

~~~bash
.env/bin/python -m src.cli measure \
  --code-file workspace/bracket.py \
  --name bracket
~~~

Typical fields include bounding box dimensions, volume, surface area, and entity counts.

---

## Agent workflow pattern (recommended)

1. Write/modify a CAD executable file in `workspace/`.
2. Run `build`.
3. Run `render` (usually `3d` + `multiview`).
4. Inspect output image(s), iterate code.
5. Run `measure` to verify constraints.
6. Run `export` (`stl` or `step`) when finalized.

---

## Quick command recipes

### “I changed dimensions, show me updated iso render”

~~~bash
.env/bin/python -m src.cli render \
  --code-file workspace/part.py \
  --name part \
  --mode 3d \
  --view iso \
  --output renders/part_iso.png
~~~

### “Give me production handoff files (STEP + STL)”

~~~bash
.env/bin/python -m src.cli export --code-file workspace/part.py --name part --format step --output exports/part.step
.env/bin/python -m src.cli export --code-file workspace/part.py --name part --format stl  --output exports/part.stl
~~~

### “Validate envelope before export”

~~~bash
.env/bin/python -m src.cli measure \
  --code-file workspace/part.py \
  --name part
~~~

---

## Output conventions

- Renders go to `renders/` by default.
- Exports go to `workspace/` unless `--output` is provided.
- Command output is JSON so agents can parse reliably.

---

## Troubleshooting

- **Build fails with syntax/runtime errors**  
  Validate Python and build123d usage in `--code-file`.

- **No geometry found**  
  Ensure final shape is assigned to `result`.

- **Render errors**  
  Confirm dependencies are installed in the active venv.

- **Unexpected export filename/path**  
  Pass explicit `--output` with full target file path.

---

## References

- `src/cli.py` — command interface
- `src/cad_engine.py` — execution + model handling
- `src/renderer.py` — rendering pipeline
- `examples/` — sample CAD scripts
- build123d docs: <https://build123d.readthedocs.io/>