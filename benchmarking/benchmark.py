"""Human-verified releases with hashed references and exact frozen workflow inputs."""
import hashlib
import json
import shutil
from pathlib import Path
from benchmarking.schema import Benchmark
from researcher.general import validate_sources

def canonical_hash(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    value = dict(value)
    value.pop("sha256", None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def asset_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Snapshot must be an existing file inside the benchmark directory")
    return path

def verify_assets(benchmark, root):
    for task in benchmark.tasks:
        if task.verification_status != "verified":
            continue
        snapshots = {}
        for ref in task.reference_sources:
            path = asset_path(root, ref.snapshot_path)
            if file_hash(path) != ref.sha256:
                raise ValueError("Reference snapshot hash mismatch")
            snapshots[ref.source_id] = path.read_text(encoding="utf-8")
        for fact in task.reference_facts:
            if fact.excerpt not in snapshots[fact.source_id]:
                raise ValueError("Reference excerpt not present in its frozen snapshot")
        path = asset_path(root, task.input_snapshot)
        if file_hash(path) != task.input_sha256:
            raise ValueError("Workflow input snapshot hash mismatch")
        validate_sources(json.loads(path.read_text(encoding="utf-8")))

def load_benchmark(path, *, require_frozen=False):
    path = Path(path)
    result = Benchmark.model_validate_json(path.read_text(encoding="utf-8"))
    if require_frozen and result.status != "frozen":
        raise ValueError("Live experiments require a frozen, verified benchmark")
    if result.status == "frozen":
        if result.sha256 != canonical_hash(result):
            raise ValueError("Frozen benchmark checksum mismatch; create a new version")
        verify_assets(result, path.parent)
    return result

def freeze_benchmark(draft_path, releases_dir, version):
    draft_path = Path(draft_path)
    draft = load_benchmark(draft_path)
    if draft.status != "draft":
        raise ValueError("Create a draft of a new version instead of modifying a frozen release")
    if version == draft.version:
        raise ValueError("Freezing requires a new version")
    # Validate the version before using it as a directory name.
    candidate = draft.model_dump(mode="json")
    candidate.update(version=version)
    Benchmark.model_validate(candidate)
    if any(t.verification_status != "verified" for t in draft.tasks):
        raise ValueError("Every task must be independently verified before freezing")
    verify_assets(draft, draft_path.parent)
    release = Path(releases_dir) / version
    release.mkdir(parents=True, exist_ok=False)
    (release / "assets").mkdir()
    # Copy exact bytes; reference answers are never passed to workflow agents.
    for task in candidate["tasks"]:
        for item, path_key, hash_key in [(task, "input_snapshot", "input_sha256")] + [
                (s, "snapshot_path", "sha256") for s in task["reference_sources"]]:
            source = asset_path(draft_path.parent, item[path_key])
            suffix = ".json" if path_key == "input_snapshot" else ".txt"
            relative = "assets/" + item[hash_key] + suffix
            destination = release / relative
            if not destination.exists():
                shutil.copyfile(source, destination)
            item[path_key] = relative
    candidate.update(status="frozen", sha256=None)
    candidate["sha256"] = canonical_hash(candidate)
    frozen = Benchmark.model_validate(candidate)
    destination = release / "benchmark.json"
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(frozen.model_dump_json(indent=2) + "\n")
    load_benchmark(destination, require_frozen=True)
    return destination
