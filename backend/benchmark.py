"""
benchmark.py — Performance evaluation script for InterviewPrepAI

Measures, using your actual rag.py functions (no mocking):
1. Session recovery time — cold rebuild (re-embed everything) vs.
   loading a persisted FAISS index from disk.
2. Perceived latency — streaming time-to-first-token vs. blocking
   full-completion LLM call.
3. Retrieval latency — time for retriever.invoke() (MMR search).
4. Index footprint — on-disk index size + chunk count, for honest
   scale reporting.

USAGE
-----
Run this from the same directory as rag.py (so the import works),
with a session that already has a resume AND job description
uploaded via the app.

    docker compose exec backend python benchmark.py --session_id <id> --runs 5

Results print to the console and are also saved to
benchmark_results.json.

CAVEAT ON THE SESSION-RECOVERY NUMBER
--------------------------------------
Running build_vector_db() then load_vector_db() back-to-back in the
same process means the OS file cache is warm for the reload, which
can make "load" look faster than a true cold restart would. This
mirrors production behavior reasonably well, but for the most
conservative number, restart the process between each pair instead
of looping in one process.
"""

import argparse
import json
import os
import statistics
import time

import rag  # import the module itself, not individual names —
            # rag.load_sessions() rebinds rag.user_documents internally,
            # and a `from rag import user_documents` copy would not see
            # that update. Always access state via rag.<name>.


def measure_session_recovery(session_id, runs=5):
    """Compare cold rebuild (re-embed everything) vs. loading a persisted FAISS index."""
    rebuild_times = []
    load_times = []

    for _ in range(runs):
        start = time.perf_counter()
        rag.build_vector_db(session_id)
        rebuild_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        rag.load_vector_db(session_id)
        load_times.append(time.perf_counter() - start)

    avg_rebuild = statistics.mean(rebuild_times)
    avg_load = statistics.mean(load_times)
    reduction = (1 - avg_load / avg_rebuild) * 100 if avg_rebuild > 0 else 0

    return {
        "avg_rebuild_seconds": round(avg_rebuild, 4),
        "avg_load_seconds": round(avg_load, 4),
        "reduction_percent": round(reduction, 1),
        "runs": runs,
    }


def measure_streaming_latency(prompt, runs=5):
    """Compare time-to-first-token (streaming) vs. full blocking completion."""
    first_token_times = []
    full_times = []

    for _ in range(runs):
        start = time.perf_counter()
        first_token = None
        for chunk in rag.llm.stream(prompt):
            if chunk.content and first_token is None:
                first_token = time.perf_counter() - start
        if first_token is not None:
            first_token_times.append(first_token)

        start = time.perf_counter()
        rag.llm.invoke(prompt)
        full_times.append(time.perf_counter() - start)

    avg_first_token = statistics.mean(first_token_times)
    avg_full = statistics.mean(full_times)
    reduction = (1 - avg_first_token / avg_full) * 100 if avg_full > 0 else 0

    return {
        "avg_time_to_first_token_seconds": round(avg_first_token, 4),
        "avg_full_completion_seconds": round(avg_full, 4),
        "perceived_latency_reduction_percent": round(reduction, 1),
        "runs": runs,
    }


def measure_retrieval_latency(session_id, queries, runs=3):
    """Time MMR-based retrieval per query."""
    retriever = rag.get_retriever(session_id)
    if retriever is None:
        raise RuntimeError(
            f"No retriever found for session {session_id}. "
            "Upload a resume + job description for this session first."
        )

    all_times = []
    for query in queries:
        for _ in range(runs):
            start = time.perf_counter()
            retriever.invoke(query)
            all_times.append(time.perf_counter() - start)

    return {
        "avg_retrieval_seconds": round(statistics.mean(all_times), 4),
        "min_seconds": round(min(all_times), 4),
        "max_seconds": round(max(all_times), 4),
        "num_queries_tested": len(queries),
        "runs_per_query": runs,
    }


def measure_index_footprint(session_id):
    """Report on-disk index size and chunk count, for honest scale claims."""
    path = rag.get_faiss_path(session_id)
    index_file = os.path.join(path, "index.faiss")
    pkl_file = os.path.join(path, "index.pkl")

    size_bytes = sum(
        os.path.getsize(f) for f in (index_file, pkl_file) if os.path.exists(f)
    )

    db = rag.load_vector_db(session_id)
    chunk_count = db.index.ntotal if db is not None else None

    return {
        "index_size_kb": round(size_bytes / 1024, 2),
        "chunk_count": chunk_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark InterviewPrepAI RAG performance")
    parser.add_argument(
        "--session_id",
        required=True,
        help="Existing session ID with resume + job description already uploaded",
    )
    parser.add_argument(
        "--runs", type=int, default=5, help="Number of runs to average per test (default: 5)"
    )
    args = parser.parse_args()

    rag.load_sessions()
    if args.session_id not in rag.user_documents:
        raise SystemExit(
            f"Session '{args.session_id}' not found in sessions.json. "
            "Upload a resume and job description via the app first, "
            "then pass that session_id here."
        )

    # Ensure this process's in-memory retriever cache is populated for this
    # session (a fresh `docker compose exec` process starts with empty
    # user_db/user_retriever dicts — only restore_sessions(), called at
    # FastAPI startup, populates those, and that ran in a *different*
    # process than this script).
    if args.session_id not in rag.user_retriever:
        db = rag.load_vector_db(args.session_id)
        if db is not None:
            rag.user_db[args.session_id] = db
            rag.user_retriever[args.session_id] = db.as_retriever(
                search_type="mmr", search_kwargs={"k": 10, "fetch_k": 30}
            )

    print(f"Benchmarking session: {args.session_id}")
    print(f"Averaging over {args.runs} run(s) per test.\n")

    print("[1/4] Session recovery time (rebuild vs. persisted load)...")
    recovery = measure_session_recovery(args.session_id, runs=args.runs)
    print(recovery, "\n")

    print("[2/4] Streaming vs. blocking latency...")
    sample_prompt = (
        # "Summarize the candidate's top 3 technical strengths based on their resume."
        "what are the gaps in my resume based on the job description?"
    )
    latency = measure_streaming_latency(sample_prompt, runs=args.runs)
    print(latency, "\n")

    print("[3/4] Retrieval latency (MMR search)...")
    sample_queries = [
        "What are the candidate's strongest technical skills?",
        "How does this candidate's experience match the job description?",
        "What projects has this candidate worked on?",
    ]
    retrieval = measure_retrieval_latency(args.session_id, sample_queries, runs=3)
    print(retrieval, "\n")

    print("[4/4] Index footprint (size + chunk count)...")
    footprint = measure_index_footprint(args.session_id)
    print(footprint, "\n")

    results = {
        "session_recovery": recovery,
        "streaming_latency": latency,
        "retrieval_latency": retrieval,
        "index_footprint": footprint,
    }

    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Full results saved to benchmark_results.json")
    print(
        "\nNote: session-recovery numbers were measured in a single warm process "
        "(OS file cache warm on reload). For the most conservative number, "
        "re-run load_vector_db() in a fresh process instead."
    )


if __name__ == "__main__":
    main()
