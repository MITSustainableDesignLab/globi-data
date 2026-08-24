"""The ``globi-data`` command line interface.

Inputs are designed to be usable without this CLI at all — browse them on
GitHub and download what you need. The CLI is for the people who maintain the
repository, and for CI.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import check as check_mod
from . import gitutil, paths, registry, render
from . import index as index_mod
from . import inputs as inputs_mod
from . import outputs as outputs_mod
from . import status as status_mod
from .models import Author
from .paths import GlobiDataError

console = Console()
err_console = Console(stderr=True)


def _root(ctx: click.Context) -> Path:
    """Return the resolved repo root from the context."""
    return ctx.obj["root"]


def _partners_repo(explicit: str | None, root: Path) -> Path | None:
    """Locate globi-partners-data: explicit flag, env var, then the sibling directory."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("GLOBI_PARTNERS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    sibling = root.parent / "globi-partners-data"
    return sibling if sibling.is_dir() else None


def _fail(message: str) -> None:
    """Print an error and exit non-zero."""
    err_console.print(f"[bold red]error[/] {message}")
    sys.exit(1)


@click.group()
@click.option("--root", "root_opt", default=None, help="Path to the globi-data repo.")
@click.pass_context
def cli(ctx: click.Context, root_opt: str | None) -> None:
    """Versioned inputs and outputs for GloBI simulation runs."""
    ctx.ensure_object(dict)
    try:
        ctx.obj["root"] = (
            Path(root_opt).expanduser().resolve() if root_opt else paths.repo_root()
        )
    except GlobiDataError as exc:
        _fail(str(exc))


# --------------------------------------------------------------------------- #
# inputs
# --------------------------------------------------------------------------- #


@cli.group()
def inputs() -> None:
    """Work with versioned input bundles."""


@inputs.command("list")
@click.option("--partner", default=None, help="Only show this partner.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def inputs_list(ctx: click.Context, partner: str | None, as_json: bool) -> None:
    """List every partner and its current input version."""
    root = _root(ctx)
    rows = []
    for name in paths.list_partners(root):
        if partner and name != partner:
            continue
        pdir = paths.partner_dir(root, name)
        current = paths.resolve_version(pdir, "current")
        manifest = inputs_mod.read_manifest(pdir / current)
        rows.append({
            "partner": name,
            "current": current,
            "versions": len(paths.list_versions(pdir)),
            "impact": manifest.impact,
            "updated": manifest.created_at,
            "kind": manifest.globi.bundle_kind,
            "bytes": manifest.totals.size_bytes,
        })

    if as_json:
        console.print_json(json.dumps(rows))
        return

    table = Table(title="Input bundles")
    for column in ("Partner", "Current", "Versions", "Kind", "Size", "Updated"):
        table.add_column(column)
    for row in rows:
        table.add_row(
            row["partner"],
            row["current"],
            str(row["versions"]),
            row["kind"],
            render._bytes(row["bytes"]),
            row["updated"][:10],
        )
    console.print(table)


@inputs.command("show")
@click.argument("partner")
@click.argument("version", default="current")
@click.pass_context
def inputs_show(ctx: click.Context, partner: str, version: str) -> None:
    """Show the contents and fingerprints of one input version."""
    root = _root(ctx)
    pdir = paths.partner_dir(root, partner)
    try:
        resolved = paths.resolve_version(pdir, version)
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    manifest = inputs_mod.read_manifest(pdir / resolved)

    console.print(f"[bold]{partner} {resolved}[/]  ({manifest.impact})")
    console.print(manifest.summary.strip())
    console.print(f"bundle_sha256: [dim]{manifest.bundle_sha256}[/]")
    if manifest.parent_version:
        console.print(f"parent: {manifest.parent_version}")

    table = Table(title="Files")
    for column in ("File", "Role", "Size", "sha256"):
        table.add_column(column)
    for entry in manifest.files:
        table.add_row(
            entry.path,
            entry.role or "",
            render._bytes(entry.size_bytes),
            entry.sha256[:12],
        )
    console.print(table)

    if manifest.external_files:
        table = Table(title="Not stored here")
        for column in ("File", "Size", "Location", "sha256"):
            table.add_column(column)
        for ext in manifest.external_files:
            table.add_row(
                ext.path,
                render._bytes(ext.size_bytes),
                f"{ext.stored_in.repo}/{ext.stored_in.path}",
                (ext.sha256 or "")[:12],
            )
        console.print(table)


@inputs.command("current")
@click.argument("partner")
@click.pass_context
def inputs_current(ctx: click.Context, partner: str) -> None:
    """Print the current version label for a partner."""
    root = _root(ctx)
    try:
        click.echo(paths.resolve_version(paths.partner_dir(root, partner), "current"))
    except GlobiDataError as exc:
        _fail(str(exc))


@inputs.command("path")
@click.argument("partner")
@click.option("--role", required=True, help="Role to resolve, e.g. db_file.")
@click.option("--version", default="current")
@click.pass_context
def inputs_path(ctx: click.Context, partner: str, role: str, version: str) -> None:
    """Print the absolute path of one role's file, for use in shell scripts."""
    root = _root(ctx)
    pdir = paths.partner_dir(root, partner)
    try:
        resolved = paths.resolve_version(pdir, version)
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    manifest = inputs_mod.read_manifest(pdir / resolved)
    value = manifest.role_path(role)
    if value is None:
        _fail(f"{partner} {resolved} has no file for role {role!r}.")
        return
    if value.startswith(("http://", "https://", "s3://")):
        click.echo(value)
    elif value.startswith("external:"):
        click.echo(value.split(":", 1)[1])
    else:
        click.echo(str(pdir / resolved / value))


@inputs.command("new")
@click.argument("partner")
@click.option("--from", "source", required=True, help="Directory to assemble from.")
@click.option("--summary", default="", help="One line describing what changed.")
@click.option(
    "--impact",
    type=click.Choice(["auto", "simulation-affecting", "metadata-only"]),
    default="auto",
)
@click.option("--include", "extra", multiple=True, help="Force-include a glob.")
@click.option(
    "--allow-noop", is_flag=True, help="Permit a version identical to its parent."
)
@click.option(
    "--no-hash-external", is_flag=True, help="Skip hashing large external files."
)
@click.option(
    "--dry-run", is_flag=True, help="Report what would happen, write nothing."
)
@click.pass_context
def inputs_new(
    ctx: click.Context,
    partner: str,
    source: str,
    summary: str,
    impact: str,
    extra: tuple[str, ...],
    allow_noop: bool,
    no_hash_external: bool,
    dry_run: bool,
) -> None:
    """Create the next input version for PARTNER."""
    root = _root(ctx)
    if allow_noop and not summary:
        _fail("--allow-noop requires a --summary explaining why.")
    repo = _partners_repo(None, root)
    scenarios = (
        registry.load_partner_scenarios(repo / "data" / "experiments.yaml").get(partner)
        if repo
        else None
    )
    try:
        result = inputs_mod.create_version(
            root,
            partner,
            Path(source).expanduser().resolve(),
            summary=summary or f"Import {partner} inputs.",
            impact=impact,
            extra_includes=extra,
            scenarios=scenarios,
            allow_noop=allow_noop,
            hash_external=not no_hash_external,
            dry_run=dry_run,
        )
    except GlobiDataError as exc:
        _fail(str(exc))
        return

    m = result.manifest
    verb = "would create" if dry_run else "created"
    console.print(
        f"[bold green]{verb}[/] {partner} [bold]{m.version}[/] "
        f"({m.totals.file_count} files, {render._bytes(m.totals.size_bytes)}, {m.impact})"
    )
    changed = list(m.changes)
    if changed:
        console.print(f"  {len(changed)} file(s) changed from {m.parent_version}:")
        for change in changed[:10]:
            console.print(f"    [cyan]{change.change:9}[/] {change.path}")
        if len(changed) > 10:
            console.print(f"    ... and {len(changed) - 10} more")
    if result.plan.skipped:
        console.print(
            f"  [yellow]{len(result.plan.skipped)} file(s) not carried over[/]"
        )
        for rel, reason in result.plan.skipped[:8]:
            console.print(f"    [dim]{rel} — {reason}[/]")
        if len(result.plan.skipped) > 8:
            console.print(f"    [dim]... and {len(result.plan.skipped) - 8} more[/]")
    for warning in result.plan.warnings:
        console.print(f"  [yellow]warning[/] {warning}")
    if not dry_run:
        rel = result.version_dir.relative_to(root)
        console.print(
            f"\nNext: [bold]git add {rel} inputs published.yml && git commit[/]"
        )


@inputs.command("finalize")
@click.argument("partner")
@click.argument("version")
@click.pass_context
def inputs_finalize(ctx: click.Context, partner: str, version: str) -> None:
    """Recompute hashes for a draft version and rewrite its manifest."""
    root = _root(ctx)
    try:
        manifest = inputs_mod.finalize_version(root, partner, version)
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    console.print(
        f"[bold green]finalized[/] {partner} {version}: "
        f"{manifest.totals.file_count} files, {manifest.impact}, "
        f"bundle_sha256 {manifest.bundle_sha256[:12]}..."
    )


@inputs.command("diff")
@click.argument("partner")
@click.argument("version_a")
@click.argument("version_b")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def inputs_diff(
    ctx: click.Context, partner: str, version_a: str, version_b: str, as_json: bool
) -> None:
    """Compare two input versions file by file."""
    root = _root(ctx)
    try:
        diffs = inputs_mod.diff_versions(root, partner, version_a, version_b)
    except GlobiDataError as exc:
        _fail(str(exc))
        return

    if as_json:
        console.print_json(json.dumps([d.__dict__ for d in diffs]))
        return
    if not diffs:
        console.print(f"{partner} {version_a} and {version_b} are identical.")
        return

    table = Table(title=f"{partner}: {version_a} → {version_b}")
    for column in ("File", "Change", "Before", "After"):
        table.add_column(column)
    colours = {"added": "green", "removed": "red", "modified": "yellow"}
    for diff in diffs:
        table.add_row(
            diff.path,
            f"[{colours.get(diff.change, 'white')}]{diff.change}[/]",
            render._bytes(diff.old_bytes),
            render._bytes(diff.new_bytes),
        )
    console.print(table)


@inputs.command("verify")
@click.argument("partner", required=False)
@click.option("--version", default=None, help="Only this version.")
@click.option(
    "--all", "check_all", is_flag=True, help="Every version, not just current."
)
@click.option("--gis-root", default=None, help="Where buildings.geojson files live.")
@click.option("--hash-gis", is_flag=True, help="Also hash external GIS files (slow).")
@click.pass_context
def inputs_verify(
    ctx: click.Context,
    partner: str | None,
    version: str | None,
    check_all: bool,
    gis_root: str | None,
    hash_gis: bool,
) -> None:
    """Re-hash stored files and check them against their manifests."""
    root = _root(ctx)
    gis = Path(gis_root).expanduser().resolve() if gis_root else None
    if gis is None:
        repo = _partners_repo(None, root)
        if repo:
            gis = repo / "data" / "partners"

    targets = [partner] if partner else paths.list_partners(root)
    total = 0
    problems = 0
    for name in targets:
        pdir = paths.partner_dir(root, name)
        versions = (
            [version]
            if version
            else (
                paths.list_versions(pdir)
                if check_all
                else [paths.resolve_version(pdir, "current")]
            )
        )
        for candidate in versions:
            total += 1
            issues = inputs_mod.verify_version(
                root, name, candidate, gis_root=gis, hash_gis=hash_gis
            )
            for issue in issues:
                problems += issue.level == "error"
                colour = "red" if issue.level == "error" else "yellow"
                console.print(
                    f"[{colour}]{issue.level}[/] {name}/{candidate}/{issue.path}: {issue.message}"
                )

    if problems:
        err_console.print(
            f"[bold red]{problems} problem(s) across {total} version(s).[/]"
        )
        sys.exit(1)
    console.print(f"[bold green]ok[/] {total} version(s) verified.")


@inputs.command("bundle")
@click.argument("partner")
@click.option("--version", default="current")
@click.option("--out", "out_path", required=True, help="Destination .zip path.")
@click.pass_context
def inputs_bundle(
    ctx: click.Context, partner: str, version: str, out_path: str
) -> None:
    """Zip one input version for sharing."""
    import zipfile

    root = _root(ctx)
    pdir = paths.partner_dir(root, partner)
    try:
        resolved = paths.resolve_version(pdir, version)
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    version_dir = pdir / resolved
    target = Path(out_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(version_dir.rglob("*")):
            if path.is_file():
                archive.write(
                    path, f"{partner}-{resolved}/{path.relative_to(version_dir)}"
                )
    console.print(
        f"[bold green]wrote[/] {target} ({render._bytes(target.stat().st_size)})"
    )


@inputs.command("retract")
@click.argument("partner")
@click.argument("version")
@click.option("--reason", required=True, help="Why this version should not be used.")
@click.pass_context
def inputs_retract(ctx: click.Context, partner: str, version: str, reason: str) -> None:
    """Mark a version as retracted without editing its frozen directory."""
    root = _root(ctx)
    try:
        inputs_mod.retract_version(root, partner, version, reason)
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    console.print(f"[yellow]retracted[/] {partner} {version}: {reason}")


@inputs.command("draft")
@click.argument("partner")
@click.option("--summary", required=True, help="What this version will change.")
@click.pass_context
def inputs_draft(ctx: click.Context, partner: str, summary: str) -> None:
    """Start the next version as an editable copy of the current one.

    Used by the browser-based flow: the draft can be edited through GitHub's web
    UI and is promoted to current only when its pull request merges.
    """
    root = _root(ctx)
    try:
        manifest = inputs_mod.draft_version(
            root, partner, summary=summary, author=_git_author(root)
        )
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    console.print(
        f"[bold green]drafted[/] {partner} [bold]{manifest.version}[/] "
        f"(copy of {manifest.parent_version}) — edit it, then promote on merge."
    )


@inputs.command("promote")
@click.argument("partner")
@click.argument("version")
@click.pass_context
def inputs_promote(ctx: click.Context, partner: str, version: str) -> None:
    """Publish a draft version: make it current and freeze it."""
    root = _root(ctx)
    try:
        manifest = inputs_mod.promote_version(root, partner, version)
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    console.print(
        f"[bold green]promoted[/] {partner} [bold]{manifest.version}[/] "
        f"({manifest.impact}) — now current and frozen."
    )


# --------------------------------------------------------------------------- #
# outputs
# --------------------------------------------------------------------------- #


@cli.group()
def outputs() -> None:
    """Work with recorded run results."""


@outputs.command("list")
@click.option("--experiment", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def outputs_list(ctx: click.Context, experiment: str | None, as_json: bool) -> None:
    """List every experiment with recorded results."""
    root = _root(ctx)
    rows = []
    for name in paths.list_experiments(root):
        if experiment and name != experiment:
            continue
        edir = paths.experiment_dir(root, name)
        current = paths.resolve_version(edir, "current")
        manifest = outputs_mod.read_output_manifest(edir / current)
        rows.append({
            "experiment": name,
            "version": current,
            "scythe_version": manifest.version,
            "run_timestamp": manifest.run_timestamp,
            "results": len(manifest.result_files),
            "input_version": manifest.provenance.input.version,
            "confidence": manifest.provenance.input.confidence,
        })

    if as_json:
        console.print_json(json.dumps(rows))
        return

    table = Table(title="Recorded results")
    for column in ("Experiment", "Version", "Run", "Results", "From input", "Pin"):
        table.add_column(column)
    for row in rows:
        table.add_row(
            row["experiment"],
            row["version"],
            f"{row['scythe_version']} @ {row['run_timestamp'][:10]}",
            str(row["results"]),
            row["input_version"] or "-",
            row["confidence"],
        )
    console.print(table)


@outputs.command("show")
@click.argument("experiment")
@click.argument("version", default="current")
@click.pass_context
def outputs_show(ctx: click.Context, experiment: str, version: str) -> None:
    """Show one output version's results and provenance."""
    root = _root(ctx)
    edir = paths.experiment_dir(root, experiment)
    try:
        resolved = paths.resolve_version(edir, version)
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    manifest = outputs_mod.read_output_manifest(edir / resolved)
    pin = manifest.provenance.input

    console.print(f"[bold]{experiment} {resolved}[/]")
    console.print(f"run: {manifest.version} @ {manifest.run_timestamp}")
    console.print(
        f"built from input [bold]{pin.version or '?'}[/] "
        f"([{'yellow' if pin.confidence != 'exact' else 'green'}]{pin.confidence}[/])"
    )
    code = manifest.provenance.code
    if code.globi_partners_data:
        console.print(
            f"globi-partners-data: {code.globi_partners_data.get('commit', '?')}"
        )
    if code.globi:
        console.print(f"globi: {code.globi.get('commit', '?')}")

    table = Table(title="Results")
    for column in ("Key", "Size", "URI"):
        table.add_column(column)
    for entry in manifest.result_files:
        table.add_row(entry.result_key, render._bytes(entry.size_bytes), entry.s3_uri)
    console.print(table)


@outputs.command("record")
@click.option("--experiment", required=True)
@click.option(
    "--from-csv", "from_csv", default=None, help="latest-results.csv to read."
)
@click.option("--from-s3", is_flag=True, help="Query S3 for the latest run.")
@click.option("--input-version", default=None)
@click.option("--summary", default="")
@click.option(
    "--confidence", type=click.Choice(["exact", "inferred"]), default="inferred"
)
@click.option(
    "--hash/--no-hash", "do_hash", default=False, help="Fetch object metadata."
)
@click.option("--allow-noop", is_flag=True)
@click.option("--partners-repo", default=None)
@click.pass_context
def outputs_record(
    ctx: click.Context,
    experiment: str,
    from_csv: str | None,
    from_s3: bool,
    input_version: str | None,
    summary: str,
    confidence: str,
    do_hash: bool,
    allow_noop: bool,
    partners_repo: str | None,
) -> None:
    """Record a new output version for one experiment."""
    root = _root(ctx)
    repo = _partners_repo(partners_repo, root)

    if from_csv:
        grouped = outputs_mod.load_latest_results_csv(Path(from_csv).expanduser())
        results = grouped.get(experiment)
        if not results:
            _fail(f"{experiment} not found in {from_csv}.")
            return
    elif from_s3:
        _fail(
            "--from-s3 needs the globi-partners-data result resolver. Export with "
            "`globi-partners latest-results` and pass --from-csv instead."
        )
        return
    else:
        _fail("Pass either --from-csv or --from-s3.")
        return

    sizes = outputs_mod.head_objects(results) if do_hash else None
    kinds = (
        registry.load_scenario_kinds(repo / "data" / "experiments.yaml") if repo else {}
    )
    aliases = (
        registry.load_partner_aliases(repo / "data" / "experiments.yaml")
        if repo
        else {}
    )
    manifest = outputs_mod.record_experiment(
        root,
        experiment,
        results,
        summary=summary or f"Recorded results for {experiment}.",
        input_version=input_version,
        confidence=confidence,
        partners_repo=repo,
        scenario_kinds=kinds,
        partner_aliases=aliases,
        sizes=sizes,
        allow_noop=allow_noop,
        author=_git_author(root),
    )
    if manifest is None:
        console.print(
            f"[yellow]no change[/] {experiment} already records these results."
        )
        return
    console.print(
        f"[bold green]recorded[/] {experiment} [bold]{manifest.output_version}[/] "
        f"({len(manifest.result_files)} results, input "
        f"{manifest.provenance.input.version or '?'})"
    )


@outputs.command("verify")
@click.argument("experiment", required=False)
@click.option("--all", "check_all", is_flag=True)
@click.pass_context
def outputs_verify(ctx: click.Context, experiment: str | None, check_all: bool) -> None:
    """Check that every recorded S3 object still exists."""
    root = _root(ctx)
    names = [experiment] if experiment else paths.list_experiments(root)
    if not names:
        console.print("No recorded outputs.")
        return

    missing = 0
    for name in names:
        edir = paths.experiment_dir(root, name)
        versions = (
            paths.list_versions(edir)
            if check_all
            else [paths.resolve_version(edir, "current")]
        )
        for version in versions:
            manifest = outputs_mod.read_output_manifest(edir / version)
            uris = {e.result_key: e.s3_uri for e in manifest.result_files}
            heads = outputs_mod.head_objects(uris)
            for key, (size, _etag, _modified) in heads.items():
                if size is None:
                    missing += 1
                    console.print(
                        f"[red]missing[/] {name}/{version} {key}: {uris[key]}"
                    )
    if missing:
        err_console.print(f"[bold red]{missing} object(s) unreachable.[/]")
        sys.exit(1)
    console.print("[bold green]ok[/] every recorded object is present.")


@outputs.command("download")
@click.argument("experiment")
@click.option("--version", default="current")
@click.option("--key", "keys", multiple=True, help="Only these result keys.")
@click.option("--dest", required=True)
@click.pass_context
def outputs_download(
    ctx: click.Context, experiment: str, version: str, keys: tuple[str, ...], dest: str
) -> None:
    """Download an experiment's result parquets from S3."""
    root = _root(ctx)
    edir = paths.experiment_dir(root, experiment)
    try:
        resolved = paths.resolve_version(edir, version)
    except GlobiDataError as exc:
        _fail(str(exc))
        return
    manifest = outputs_mod.read_output_manifest(edir / resolved)
    written = outputs_mod.download_results(
        manifest, Path(dest).expanduser().resolve(), keys=keys
    )
    for path in written:
        console.print(f"[green]↓[/] {path}")


# --------------------------------------------------------------------------- #
# status, index, check
# --------------------------------------------------------------------------- #


@cli.command("status")
@click.option("--partner", default=None)
@click.option("--experiment", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.option(
    "--fail-on",
    type=click.Choice(["stale", "error", "none"]),
    default="none",
    help="Exit non-zero when problems of this severity exist.",
)
@click.option("--partners-repo", default=None)
@click.pass_context
def status_cmd(
    ctx: click.Context,
    partner: str | None,
    experiment: str | None,
    as_json: bool,
    fail_on: str,
    partners_repo: str | None,
) -> None:
    """Report which results are still up to date with their inputs."""
    root = _root(ctx)
    repo = _partners_repo(partners_repo, root)
    rows = status_mod.evaluate_all(
        root, partner=partner, experiment=experiment, partners_repo=repo
    )

    if as_json:
        console.print_json(json.dumps([row.__dict__ for row in rows]))
    elif not rows:
        console.print("No recorded outputs to check.")
    else:
        table = Table(title="Results status")
        for column in ("Experiment", "State", "Built from", "Current input", "Detail"):
            table.add_column(column)
        colours = {
            "ok": "green",
            "stale": "red",
            "tampered": "red",
            "broken-pin": "red",
            "code-drift": "yellow",
            "metadata-drift": "blue",
            "inferred": "dim",
            "unpinned": "dim",
        }
        for row in rows:
            colour = colours.get(row.state, "white")
            table.add_row(
                row.experiment,
                f"[{colour}]{row.state}[/]",
                row.pinned_version or "-",
                row.current_version or "-",
                row.detail,
            )
        console.print(table)

    if fail_on == "stale" and any(row.is_problem for row in rows):
        sys.exit(1)
    if fail_on == "error" and any(
        row.state in {"broken-pin", "tampered"} for row in rows
    ):
        sys.exit(1)


@cli.command("index")
@click.option("--write", "do_write", is_flag=True, help="Apply changes.")
@click.option(
    "--check", "do_check", is_flag=True, help="Fail if anything is out of date."
)
@click.option("--partners-repo", default=None)
@click.pass_context
def index_cmd(
    ctx: click.Context, do_write: bool, do_check: bool, partners_repo: str | None
) -> None:
    """Regenerate the index files, READMEs and status page."""
    root = _root(ctx)
    repo = _partners_repo(partners_repo, root)
    if not do_write and not do_check:
        do_check = True

    changes = index_mod.rebuild(root, write=do_write, partners_repo=repo)
    if not changes:
        console.print("[bold green]ok[/] generated files are up to date.")
        return
    for change in changes:
        verb = "wrote" if do_write else change.reason
        console.print(f"[yellow]{verb}[/] {change.path.relative_to(root)}")
    if do_check and not do_write:
        err_console.print(
            f"[bold red]{len(changes)} generated file(s) out of date.[/] "
            "Run `globi-data index --write`."
        )
        sys.exit(1)


@cli.command("check")
@click.option("--offline/--online", default=True)
@click.option("--since", default=None, help="Ref to enforce immutability against.")
@click.option("--gis-root", default=None)
@click.option("--partners-repo", default=None)
@click.pass_context
def check_cmd(
    ctx: click.Context,
    offline: bool,
    since: str | None,
    gis_root: str | None,
    partners_repo: str | None,
) -> None:
    """Run every validation CI performs."""
    root = _root(ctx)
    repo = _partners_repo(partners_repo, root)
    gis = Path(gis_root).expanduser().resolve() if gis_root else None
    if gis is None and repo:
        gis = repo / "data" / "partners"

    problems = check_mod.run_checks(
        root, offline=offline, gis_root=gis, partners_repo=repo, since=since
    )
    errors = [p for p in problems if p.level == "error"]
    for problem in problems:
        colour = "red" if problem.level == "error" else "yellow"
        console.print(
            f"[{colour}]{problem.level}[/] {problem.where}: {problem.message}"
        )

    if errors:
        err_console.print(f"[bold red]{len(errors)} error(s).[/]")
        sys.exit(1)
    console.print("[bold green]ok[/] all checks passed.")


@cli.command("check-staged")
@click.pass_context
def check_staged(ctx: click.Context) -> None:
    """Reject staged edits to published version directories (pre-commit hook)."""
    root = _root(ctx)
    problems = check_mod.check_immutability(root, staged=True)
    if not problems:
        return
    err_console.print(
        "[bold red]Refusing to commit: published versions are frozen.[/]\n"
    )
    for problem in problems:
        err_console.print(f"  {problem.where}\n    {problem.message}")
    err_console.print(
        "\nA published version is a permanent record. To change these inputs, create a"
        "\nnew version instead:\n"
        '\n    globi-data inputs new <partner> --from <source> --summary "what changed"\n'
        "\nTo correct a version that should not be used, retract it — that edits"
        "\nversions.yml, not the frozen directory:\n"
        '\n    globi-data inputs retract <partner> <version> --reason "..."\n'
    )
    sys.exit(1)


@cli.command("init-hooks")
@click.pass_context
def init_hooks(ctx: click.Context) -> None:
    """Point git at this repo's hooks directory."""
    root = _root(ctx)
    result = gitutil._run(["config", "core.hooksPath", ".githooks"], root)
    if result is None:
        _fail("Could not configure git hooks.")
    console.print("[bold green]ok[/] git will now run .githooks/pre-commit.")


def _git_author(root: Path) -> Author:
    """Read the committing identity from git config."""
    return Author(
        name=gitutil._run(["config", "user.name"], root),
        email=gitutil._run(["config", "user.email"], root),
    )


# --------------------------------------------------------------------------- #
# migrate
# --------------------------------------------------------------------------- #


@cli.group()
def migrate() -> None:
    """One-off commands for seeding this repo from globi-partners-data."""


@migrate.command("inputs")
@click.option(
    "--from", "source_repo", required=True, help="Path to globi-partners-data."
)
@click.option("--partner", "partners", multiple=True, help="Only these partners.")
@click.option("--summary", default="", help="Summary for the created versions.")
@click.option("--no-hash-external", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def migrate_inputs(
    ctx: click.Context,
    source_repo: str,
    partners: tuple[str, ...],
    summary: str,
    no_hash_external: bool,
    dry_run: bool,
) -> None:
    """Seed v001 for each partner directory in globi-partners-data."""
    root = _root(ctx)
    base = Path(source_repo).expanduser().resolve() / "data" / "partners"
    if not base.is_dir():
        _fail(f"{base} does not exist.")

    all_scenarios = registry.load_partner_scenarios(
        Path(source_repo).expanduser().resolve() / "data" / "experiments.yaml"
    )
    names = list(partners) or sorted(
        p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    for name in names:
        source = base / name
        if not source.is_dir():
            console.print(f"[yellow]skip[/] {name}: no such directory")
            continue
        if paths.list_versions(paths.partner_dir(root, name)):
            console.print(f"[dim]skip[/] {name}: already has versions")
            continue
        try:
            result = inputs_mod.create_version(
                root,
                name,
                source,
                summary=summary
                or f"Initial import of {name} inputs from globi-partners-data.",
                scenarios=all_scenarios.get(name),
                hash_external=not no_hash_external,
                dry_run=dry_run,
            )
        except GlobiDataError as exc:
            console.print(f"[red]fail[/] {name}: {exc}")
            continue
        m = result.manifest
        console.print(
            f"[green]{'would create' if dry_run else 'created'}[/] {name} {m.version}: "
            f"{m.totals.file_count} files, {render._bytes(m.totals.size_bytes)}, "
            f"{len(result.plan.skipped)} skipped"
        )


@migrate.command("outputs")
@click.option("--from", "csv_path", required=True, help="Path to latest-results.csv.")
@click.option("--input-version", default=None)
@click.option("--partners-repo", default=None)
@click.option("--hash/--no-hash", "do_hash", default=False)
@click.pass_context
def migrate_outputs(
    ctx: click.Context,
    csv_path: str,
    input_version: str | None,
    partners_repo: str | None,
    do_hash: bool,
) -> None:
    """Backfill output versions from a latest-results.csv export."""
    root = _root(ctx)
    repo = _partners_repo(partners_repo, root)
    grouped = outputs_mod.load_latest_results_csv(Path(csv_path).expanduser().resolve())
    kinds = (
        registry.load_scenario_kinds(repo / "data" / "experiments.yaml") if repo else {}
    )
    aliases = (
        registry.load_partner_aliases(repo / "data" / "experiments.yaml")
        if repo
        else {}
    )
    author = _git_author(root)

    created = skipped = 0
    for experiment in sorted(grouped):
        results = grouped[experiment]
        sizes = outputs_mod.head_objects(results) if do_hash else None
        try:
            manifest = outputs_mod.record_experiment(
                root,
                experiment,
                results,
                summary=(
                    "Backfilled from latest-results.csv; first recorded results for "
                    "this experiment."
                ),
                input_version=input_version,
                confidence="inferred",
                partners_repo=repo,
                scenario_kinds=kinds,
                partner_aliases=aliases,
                sizes=sizes,
                author=author,
            )
        except GlobiDataError as exc:
            console.print(f"[red]fail[/] {experiment}: {exc}")
            continue
        if manifest is None:
            skipped += 1
            continue
        created += 1
        console.print(
            f"[green]recorded[/] {experiment} {manifest.output_version} "
            f"({len(manifest.result_files)} results, input "
            f"{manifest.provenance.input.version or '?'})"
        )
    console.print(f"\n[bold]{created} recorded, {skipped} unchanged.[/]")


if __name__ == "__main__":
    cli()
