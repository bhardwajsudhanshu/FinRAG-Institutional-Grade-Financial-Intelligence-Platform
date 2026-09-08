"""Vertex AI Vector Search benchmark (ADR-005, exp_052, STEP_029).

Full lifecycle in one process with GUARANTEED teardown:
create index -> create endpoint -> deploy -> upsert 4447 (mock vectors,
$0) -> 139-Q parity+latency benchmark -> undeploy -> delete endpoint ->
delete index. Teardown runs in `finally`, so Ctrl-C / errors still clean
up. If this process is ever killed hard (timeout, power loss), rerun with
--teardown-only to remove anything named `finrag-bench-*` (prevents the
~$0.10/hr idle burn — see docs/01_setup.md section 4d).

Usage:
    uv run python scripts/benchmark_vertex_search.py --out results/benchmarks/vertex_search.json
    uv run python scripts/benchmark_vertex_search.py --teardown-only   # emergency cleanup

Wall time is dominated by endpoint deploy (~30-60 min). Benchmark itself
is ~15 min. Total budget ~2.5h. Same parity methodology as the local
harness (top-1 + set overlap vs brute force); mock embeddings ($0) —
latency/parity don't depend on provenance.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.benchmark_vectordb import _load_eval_chunks, _percentile

INDEX_PREFIX = "finrag-bench-index"
ENDPOINT_PREFIX = "finrag-bench-endpoint"
# NOTE: the deployed-index ID is per-run (timestamped in main), NOT a
# constant — GCP rejects reusing an ID that is still propagating deletion
# from a previous failed deploy (STEP_029: fixed ID collided with the
# prior attempt's failed-state entry).
DIMENSIONS = 768


def _init(project: str, region: str):
    from google.cloud import aiplatform

    aiplatform.init(project=project, location=region)
    return aiplatform


def _teardown_matching(aiplatform, dry_run: bool = False) -> list[str]:
    """Undeploy + delete every finrag-bench index/endpoint. Returns log lines."""
    log: list[str] = []
    for ep in aiplatform.MatchingEngineIndexEndpoint.list():
        name = ep.display_name or ""
        if not name.startswith(ENDPOINT_PREFIX):
            continue
        for dep in list(ep.deployed_indexes or []):
            did = dep.id if hasattr(dep, "id") else dep.get("id")
            log.append(f"undeploy {did} from {name}")
            print(" ", log[-1], flush=True)
            if not dry_run:
                ep.undeploy_index(deployed_index_id=did)
        log.append(f"delete endpoint {name}")
        print(" ", log[-1], flush=True)
        if not dry_run:
            ep.delete()
    for ix in aiplatform.MatchingEngineIndex.list():
        name = ix.display_name or ""
        if not name.startswith(INDEX_PREFIX):
            continue
        log.append(f"delete index {name}")
        print(" ", log[-1], flush=True)
        if not dry_run:
            ix.delete()
    return log


def main() -> int:
    from finrag.config import get_settings
    from finrag.retrieval import InMemoryIndex

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("results/benchmarks/vertex_search.json"))
    parser.add_argument("--teardown-only", action="store_true")
    parser.add_argument("--machine-type", default="e2-standard-2")
    args = parser.parse_args()

    settings = get_settings()
    project = settings.gcp_project_id
    if not project:
        print("[FAIL] GCP_PROJECT_ID is empty — set it in .env", file=sys.stderr)
        return 2
    aiplatform = _init(project, settings.gcp_region)

    if args.teardown_only:
        lines = _teardown_matching(aiplatform)
        print(f"[teardown] {len(lines)} action(s):")
        for line in lines:
            print(f"  {line}")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    index_name = f"{INDEX_PREFIX}-{stamp}"
    endpoint_name = f"{ENDPOINT_PREFIX}-{stamp}"
    deployed_id = f"finrag_bench_{stamp.replace('-', '_')}"
    index = endpoint = None
    t_all = time.perf_counter()
    try:
        print(f"[1/6] creating index {index_name} ...", flush=True)
        # NOTE: leaf_* args are REQUIRED, not optional — without them the
        # SDK sends algorithm_config=None and the server 400s (STEP_029).
        # shard_size SMALL pairs with e2-standard-2 (the SDK MEDIUM default
        # rejects e2-standard-2 at deploy — second 400, same step).
        # index_update_method STREAM_UPDATE enables streaming upserts
        # (default BATCH_UPDATE only accepts GCS delta files — third 400).
        index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name=index_name,
            dimensions=DIMENSIONS,
            approximate_neighbors_count=10,
            distance_measure_type="DOT_PRODUCT_DISTANCE",
            leaf_node_embedding_count=500,
            leaf_nodes_to_search_percent=10,
            shard_size="SHARD_SIZE_SMALL",
            index_update_method="STREAM_UPDATE",
        )
        print("[2/6] creating endpoint ...", flush=True)
        endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
            display_name=endpoint_name, public_endpoint_enabled=True)
        print(f"[3/6] deploying ({args.machine_type}; ~30-60 min) ...", flush=True)
        t_deploy = time.perf_counter()
        endpoint.deploy_index(
            index=index, deployed_index_id=deployed_id,
            machine_type=args.machine_type,
            min_replica_count=1, max_replica_count=1)
        deploy_s = time.perf_counter() - t_deploy
        print(f"[3/6] deployed in {deploy_s:.0f}s", flush=True)

        print("[4/6] loading eval chunks + mock embeddings ($0) ...", flush=True)
        chunks, qa = _load_eval_chunks()
        mem = InMemoryIndex()
        from finrag.embeddings import MockEmbedder

        mock = MockEmbedder(dim=DIMENSIONS)
        vectors = mock.embed_batch([c.text for c in chunks])
        for c, v in zip(chunks, vectors, strict=True):
            mem.add(c, v)
        print("[4/6] upserting 4447 datapoints (throttled, STEP_029) ...", flush=True)
        from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

        def _is_quota_error(e: Exception) -> bool:
            return "Quota exceeded" in str(e) or "ResourceExhausted" in type(e).__name__

        @retry(retry=retry_if_exception(_is_quota_error),
               stop=stop_after_attempt(6),
               wait=wait_exponential(multiplier=30, min=30, max=300),
               reraise=True)
        def _upsert_batch(batch: list) -> None:
            index.upsert_datapoints(datapoints=batch)

        # NOTE: attempt 3 died here — 4x1000-point batches back-to-back
        # tripped the per-minute stream-update throughput quota (429).
        # 250-point batches (~0.8MB) paced 20s apart stay under it; the
        # retry above is the backstop, not the plan.
        t_up = time.perf_counter()
        step, pause_s = 250, 20.0
        for n, start in enumerate(range(0, len(chunks), step)):
            batch = [{"datapoint_id": c.chunk_id, "feature_vector": list(v)}
                     for c, v in zip(chunks[start:start + step],
                                     vectors[start:start + step], strict=True)]
            _upsert_batch(batch)
            if start + step < len(chunks):
                time.sleep(pause_s)
        upsert_s = time.perf_counter() - t_up

        print("[5/6] benchmarking 139 queries ...", flush=True)
        mem_lat, vs_lat, top1, overlap = [], [], 0, []
        # Same mock embedder for questions (parity methodology).
        qvecs = mock.embed_batch([q["question"] for q in qa])
        for qv in qvecs:
            t = time.perf_counter()
            exp_ids = [c.chunk_id for c, _ in mem.query(qv, top_k=5)]
            mem_lat.append((time.perf_counter() - t) * 1000)
            t = time.perf_counter()
            neighbors = endpoint.find_neighbors(
                deployed_index_id=deployed_id,
                queries=[list(qv)], num_neighbors=5)[0]
            vs_lat.append((time.perf_counter() - t) * 1000)
            got_ids = [n.id for n in neighbors]
            top1 += int(bool(got_ids) and bool(exp_ids) and got_ids[0] == exp_ids[0])
            overlap.append(len(set(got_ids) & set(exp_ids)) / max(1, len(exp_ids)))
        result = {
            "n_chunks": len(chunks), "n_questions": len(qa),
            "backend": "vertex-vector-search", "machine_type": args.machine_type,
            "index": index_name, "endpoint": endpoint_name,
            "deploy_s": round(deploy_s, 1), "upsert_s": round(upsert_s, 1),
            "wall_s": round(time.perf_counter() - t_all, 1),
            "in_memory": {"p50_ms": round(_percentile(mem_lat, 50), 2),
                          "p95_ms": round(_percentile(mem_lat, 95), 2)},
            "store": {"p50_ms": round(_percentile(vs_lat, 50), 2),
                      "p95_ms": round(_percentile(vs_lat, 95), 2)},
            "parity_top1_rate": round(top1 / len(qa), 4),
            "parity_set_overlap_mean": round(statistics.fmean(overlap), 4),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
        return 0
    finally:
        print("[6/6] TEARDOWN (undeploy -> delete endpoint -> delete index) ...", flush=True)
        try:
            if endpoint is not None:
                try:
                    endpoint.undeploy_index(deployed_index_id=deployed_id)
                    print("  undeployed", flush=True)
                except Exception as e:
                    print(f"  undeploy note: {e}", flush=True)
                try:
                    endpoint.delete()
                    print("  endpoint deleted", flush=True)
                except Exception as e:
                    print(f"  endpoint delete note: {e}", flush=True)
            if index is not None:
                try:
                    index.delete()
                    print("  index deleted", flush=True)
                except Exception as e:
                    print(f"  index delete note: {e}", flush=True)
        except Exception as e:
            print(f"  teardown error (rerun --teardown-only): {e}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
