#!/usr/bin/env python3
"""
Native CLI for CAD Agent.

Commands:
- build: execute build123d code from a file
- render: build then render PNG output
- export: build then export STL/STEP/3MF
- measure: build then print geometry measurements
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any

from src.cad_engine import CADEngine
from src.renderer import RenderConfig, Renderer


def _read_code(code_file: str) -> str:
    path = Path(code_file)
    if not path.exists():
        raise FileNotFoundError(f"Code file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Expected a file path, got: {path}")
    return path.read_text(encoding="utf-8")


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, default=str), flush=True)


def _debug(msg: str) -> None:
    print(f"[cad-agent][debug] {msg}", file=sys.stderr, flush=True)


def _resolve_output_path(output: str | None, default_path: Path) -> Path:
    if not output:
        return default_path

    out = Path(output)
    if out.exists() and out.is_dir():
        return out / default_path.name
    if str(output).endswith("/") or str(output).endswith("\\"):
        return out / default_path.name
    return out


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _build_engine(args: argparse.Namespace) -> tuple[CADEngine, str]:
    engine = CADEngine(workspace=Path(args.workspace))
    code = _read_code(args.code_file)
    result = engine.execute_code(code, args.name)

    if not result.get("success"):
        _print_json(result)
        raise RuntimeError("Build failed")

    return engine, code


def cmd_build(args: argparse.Namespace) -> int:
    try:
        _debug(
            f"build: start code_file={args.code_file} "
            f"name={args.name} workspace={args.workspace}"
        )
        engine = CADEngine(workspace=Path(args.workspace))
        code = _read_code(args.code_file)
        result = engine.execute_code(code, args.name)
        _debug(
            "build: execute_code finished "
            f"success={result.get('success')} "
            f"has_error={bool(result.get('error'))}"
        )

        _print_json(
            {
                "command": "build",
                "name": args.name,
                "code_file": str(Path(args.code_file)),
                "workspace": str(Path(args.workspace)),
                **result,
            }
        )
        return 0 if result.get("success") else 1

    except Exception as e:
        _debug(f"build: unhandled failure: {e}")
        traceback.print_exc(file=sys.stderr)
        _print_json(
            {
                "command": "build",
                "name": getattr(args, "name", None),
                "code_file": str(Path(getattr(args, "code_file", ""))),
                "workspace": str(Path(getattr(args, "workspace", ""))),
                "error": str(e),
            }
        )
        return 1


def cmd_measure(args: argparse.Namespace) -> int:
    try:
        engine, _ = _build_engine(args)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1

    measurement = engine.measure(args.name)
    _print_json(
        {
            "command": "measure",
            "name": args.name,
            "code_file": str(Path(args.code_file)),
            "workspace": str(Path(args.workspace)),
            "measurement": measurement,
        }
    )
    return 0 if "error" not in measurement else 1


def cmd_export(args: argparse.Namespace) -> int:
    try:
        engine, _ = _build_engine(args)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1

    try:
        exported = engine.export_model(args.name, args.format)
        final_path = _resolve_output_path(args.output, exported)
        if final_path != exported:
            _ensure_parent(final_path)
            shutil.copy2(exported, final_path)
        _print_json(
            {
                "command": "export",
                "name": args.name,
                "format": args.format,
                "code_file": str(Path(args.code_file)),
                "workspace": str(Path(args.workspace)),
                "path": str(final_path),
                "size_bytes": final_path.stat().st_size,
            }
        )
        return 0
    except Exception as e:
        _print_json(
            {
                "command": "export",
                "name": args.name,
                "format": args.format,
                "error": str(e),
            }
        )
        return 1


def cmd_render(args: argparse.Namespace) -> int:
    try:
        _debug(f"render: build start code_file={args.code_file} name={args.name} workspace={args.workspace}")
        engine, _ = _build_engine(args)
        _debug("render: build completed")
        model = engine.get_model(args.name)
        if not model or model.shape is None:
            raise RuntimeError(f"No model '{args.name}' found after build")
        _debug("render: model lookup completed")
    except Exception as e:
        _debug(f"render: pre-render failure: {e}")
        traceback.print_exc(file=sys.stderr)
        print(str(e), file=sys.stderr, flush=True)
        return 1

    renderer = Renderer(config=RenderConfig(), output_dir=Path(args.render_dir))

    requested = args.mode
    default_name = f"{args.name}_{requested}.png"
    output_target = _resolve_output_path(args.output, Path(args.render_dir) / default_name)
    _ensure_parent(output_target)
    _debug(
        "render: prepared "
        f"mode={requested} view={getattr(args, 'view', None)} "
        f"output_target={output_target} render_dir={args.render_dir}"
    )

    try:
        if requested == "3d":
            _debug("render: invoking renderer.render_3d")
            rendered = renderer.render_3d(model.shape, args.view, output_target.name)
            _debug(f"render: renderer.render_3d returned path={rendered}")
            if rendered != output_target:
                _debug(f"render: moving file {rendered} -> {output_target}")
                shutil.move(str(rendered), str(output_target))
            result = {"path": str(output_target), "mode": requested, "view": args.view}

        elif requested == "2d":
            _debug("render: invoking renderer.render_2d")
            rendered = renderer.render_2d(
                model.shape,
                view=args.view,
                with_dimensions=not args.no_dimensions,
                with_hidden=not args.no_hidden,
                filename=output_target.name,
            )
            _debug(f"render: renderer.render_2d returned path={rendered}")
            if rendered != output_target:
                _debug(f"render: moving file {rendered} -> {output_target}")
                shutil.move(str(rendered), str(output_target))
            result = {"path": str(output_target), "mode": requested, "view": args.view}

        elif requested == "multiview":
            _debug("render: invoking renderer.render_multiview")
            rendered = renderer.render_multiview(model.shape, filename=output_target.name)
            _debug(f"render: renderer.render_multiview returned path={rendered}")
            if rendered != output_target:
                _debug(f"render: moving file {rendered} -> {output_target}")
                shutil.move(str(rendered), str(output_target))
            result = {"path": str(output_target), "mode": requested}

        elif requested == "blueprint":
            _debug("render: importing BlueprintRenderer")
            from src.blueprint_renderer import BlueprintRenderer

            blueprint_renderer = BlueprintRenderer(output_dir=args.render_dir)
            views = [v.strip() for v in args.views.split(",")] if args.views else ["front", "right", "top", "bottom"]
            _debug(f"render: invoking blueprint render views={views}")
            rendered = blueprint_renderer.render_blueprint(
                model.shape,
                filename=output_target.name,
                title=args.title or args.name.upper(),
                views=views,
                custom_specs=args.specs,
            )
            rendered_path = Path(rendered)
            _debug(f"render: blueprint renderer returned path={rendered_path}")
            if rendered_path != output_target:
                _debug(f"render: moving file {rendered_path} -> {output_target}")
                shutil.move(str(rendered_path), str(output_target))
            result = {"path": str(output_target), "mode": requested, "views": views}

        else:
            raise ValueError(f"Unsupported render mode: {requested}")

        exists = output_target.exists()
        size = output_target.stat().st_size if exists else 0
        _debug(f"render: final output exists={exists} size_bytes={size} path={output_target}")

        _print_json(
            {
                "command": "render",
                "name": args.name,
                "code_file": str(Path(args.code_file)),
                "render_dir": str(Path(args.render_dir)),
                **result,
                "exists": exists,
                "size_bytes": size,
            }
        )
        return 0

    except Exception as e:
        _debug(f"render: failure in render pipeline: {e}")
        traceback.print_exc(file=sys.stderr)
        _print_json(
            {
                "command": "render",
                "name": args.name,
                "mode": requested,
                "error": str(e),
                "output_target": str(output_target),
            }
        )
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cad-agent", description="Native CAD Agent CLI")
    parser.add_argument("--workspace", default="workspace", help="Workspace directory for exports and temp files")
    parser.add_argument("--render-dir", default="renders", help="Directory for rendered images")

    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--code-file", required=True, help="Path to executable build123d Python file")
        subparser.add_argument("--name", default="default", help="Model name")

    p_build = sub.add_parser("build", help="Execute CAD code and report build status")
    add_common(p_build)
    p_build.set_defaults(func=cmd_build)

    p_measure = sub.add_parser("measure", help="Build model and print dimensions/geometry")
    add_common(p_measure)
    p_measure.set_defaults(func=cmd_measure)

    p_export = sub.add_parser("export", help="Build model and export to CAD file format")
    add_common(p_export)
    p_export.add_argument("--format", choices=["stl", "step", "3mf"], default="stl")
    p_export.add_argument("--output", help="Output file path (or directory)")
    p_export.set_defaults(func=cmd_export)

    p_render = sub.add_parser("render", help="Build model and render image")
    add_common(p_render)
    p_render.add_argument("--mode", choices=["3d", "2d", "multiview", "blueprint"], default="3d")
    p_render.add_argument("--view", default="iso", help="Render view (e.g. iso, front, right, top)")
    p_render.add_argument("--views", help="Comma-separated views for blueprint mode")
    p_render.add_argument("--title", help="Blueprint title")
    p_render.add_argument("--specs", help="Blueprint specs text")
    p_render.add_argument("--no-dimensions", action="store_true", help="Disable dimensions in 2d mode")
    p_render.add_argument("--no-hidden", action="store_true", help="Disable hidden lines in 2d mode")
    p_render.add_argument("--output", help="Output PNG file path (or directory)")
    p_render.set_defaults(func=cmd_render)

    return parser


def main(argv: list[str] | None = None) -> int:
    cmd_argv = argv if argv is not None else sys.argv[1:]
    print(f"[cad-agent] startup argv={cmd_argv}", file=sys.stderr, flush=True)

    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        return args.func(args)
    except Exception as exc:
        print(f"[cad-agent] unhandled exception: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())