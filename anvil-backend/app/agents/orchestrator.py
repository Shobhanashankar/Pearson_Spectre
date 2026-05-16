"""
LangGraph Orchestrator — the full Spectre pipeline:

Graph: ingest → [extraction ∥ research] → classifier → redline → reporter

Each node updates a shared GraphState dict.
SSE events are fired at each stage so the frontend sees live progress.
Trace spans are written to DB for the Trace Monitoring page.
"""
import asyncio, uuid, json, time
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END
import aiosqlite

from app.agents.extraction_agent import extract_clauses
from app.agents.research_agent import research_regulations
from app.agents.classifier_agent import classify_clauses
from app.agents.redline_agent import redline_findings
from app.services.notification_service import send_slack, create_github_pr
from app.services.audit_service import log_activity
from app.core.sse import sse_manager
from app.core.omium import omium_span

DB_PATH = "./spectre.db"


# ── Shared state ─────────────────────────────────────────────────────────────
class GraphState(TypedDict):
    run_id: str
    contract_id: str
    contract_name: str
    file_path: str
    file_blob: bytes
    trace_id: str
    clauses: List[Dict]
    regulation_context: Dict
    findings: List[Dict]
    enriched_findings: List[Dict]
    pr_url: Optional[str]
    error: Optional[str]


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _update_run_status(run_id: str, status: str, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        fields = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [run_id]
        if fields:
            await db.execute(f"UPDATE workflow_runs SET status=?, {fields} WHERE id=?", [status] + values)
        else:
            await db.execute("UPDATE workflow_runs SET status=? WHERE id=?", [status, run_id])
        await db.commit()


async def _save_agent_task(run_id: str, agent_name: str, status: str,
                            started_at: str = None, completed_at: str = None,
                            runtime_ms: int = None, output_data: dict = None,
                            error_msg: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agent_tasks (id, run_id, agent_name, status, started_at, completed_at, runtime_ms, output_data, error_msg)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), run_id, agent_name, status, started_at, completed_at,
             runtime_ms, json.dumps(output_data or {}), error_msg)
        )
        await db.commit()


async def _save_span(trace_id: str, run_id: str, span_name: str,
                      started_at: str, ended_at: str, latency_ms: int,
                      status: str = "ok", attributes: dict = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO trace_spans (id, trace_id, run_id, span_name, started_at, ended_at, latency_ms, status, attributes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), trace_id, run_id, span_name, started_at, ended_at,
             latency_ms, status, json.dumps(attributes or {}))
        )
        await db.commit()


async def _save_findings(findings: List[Dict]):
    async with aiosqlite.connect(DB_PATH) as db:
        for f in findings:
            await db.execute(
                """INSERT INTO findings
                   (id, run_id, contract_id, clause_text, clause_index, severity, confidence,
                    regulation_ref, regulation_body, original_text, rewrite_suggestion, regulation_cite, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    f.get("run_id"), f.get("contract_id"),
                    f.get("clause_text", ""), f.get("clause_index", 0),
                    f.get("severity", "low"), f.get("confidence", 0.0),
                    f.get("regulation_ref"), f.get("regulation_body"),
                    f.get("original_text"), f.get("rewrite_suggestion"),
                    f.get("regulation_cite"),
                    datetime.utcnow().isoformat(),
                )
            )
        await db.commit()


async def _emit(event_type: str, data: dict, run_id: str):
    await sse_manager.publish(event_type, data, run_id=run_id)
    # Also publish to global so Dashboard feed sees it
    await sse_manager.publish(event_type, data)
    # Persist to activity_feed table so the UI can load historical events
    try:
        agent = data.get("agent", "")
        title_map = {
            "agent_started": f"Agent started: {agent}",
            "agent_completed": f"Agent completed: {agent}",
            "agent_failed": f"Agent failed: {agent}",
            "pipeline_completed": "Pipeline completed",
            "pipeline_failed": "Pipeline failed",
            "contract_ingested": f"Contract ingested: {data.get('filename', '')}",
        }
        title = title_map.get(event_type, event_type)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO activity_feed (id, event_type, title, detail, related_id, related_type, created_at) VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), event_type, title, str(data), run_id, "workflow_run", datetime.utcnow().isoformat())
            )
            await db.commit()
    except Exception:
        pass


# ── Node: Extraction ──────────────────────────────────────────────────────────
async def node_extraction(state: GraphState) -> GraphState:
    t0 = time.time()
    started = datetime.utcnow().isoformat()
    run_id = state["run_id"]

    await _emit("agent_started", {"agent": "extraction", "run_id": run_id}, run_id)
    await _update_run_status(run_id, "running")

    try:
        async with omium_span(state["trace_id"], run_id, "extraction", attributes={"phase": "extraction"}):
            clauses = extract_clauses(state["file_blob"])
        elapsed = int((time.time() - t0) * 1000)
        await _save_agent_task(run_id, "extraction", "completed", started,
                                datetime.utcnow().isoformat(), elapsed, {"clause_count": len(clauses)})
        await _emit("agent_completed", {"agent": "extraction", "clause_count": len(clauses), "run_id": run_id}, run_id)
        return {**state, "clauses": clauses}
    except Exception as e:
        await _save_agent_task(run_id, "extraction", "failed", started, error_msg=str(e))
        await _emit("agent_failed", {"agent": "extraction", "error": str(e), "run_id": run_id}, run_id)
        return {**state, "error": str(e), "clauses": []}


# ── Node: Research ────────────────────────────────────────────────────────────
async def node_research(state: GraphState) -> GraphState:
    t0 = time.time()
    started = datetime.utcnow().isoformat()
    run_id = state["run_id"]

    await _emit("agent_started", {"agent": "research", "run_id": run_id}, run_id)

    try:
        async with omium_span(state["trace_id"], run_id, "research", attributes={"phase": "research"}):
            reg_context = await research_regulations(clause_texts=[c["text"] for c in state.get("clauses", [])])
        elapsed = int((time.time() - t0) * 1000)
        await _save_agent_task(run_id, "research", "completed", started,
                                datetime.utcnow().isoformat(), elapsed,
                                {"regulations": list(reg_context["rules"].keys())})
        await _emit("agent_completed", {"agent": "research", "run_id": run_id}, run_id)
        return {**state, "regulation_context": reg_context}
    except Exception as e:
        await _save_agent_task(run_id, "research", "failed", started, error_msg=str(e))
        return {**state, "regulation_context": {"rules": {}, "summary": ""}}


# ── Node: Classifier ──────────────────────────────────────────────────────────
async def node_classifier(state: GraphState) -> GraphState:
    t0 = time.time()
    started = datetime.utcnow().isoformat()
    run_id = state["run_id"]

    await _emit("agent_started", {"agent": "classifier", "run_id": run_id}, run_id)

    if state.get("error") or not state.get("clauses"):
        return {**state, "findings": []}

    try:
        async with omium_span(state["trace_id"], run_id, "classifier", attributes={"phase": "classification", "clauses": len(state.get("clauses", []))}):
            findings = await classify_clauses(
                state["clauses"], state["regulation_context"],
                state["contract_id"], run_id
            )
        elapsed = int((time.time() - t0) * 1000)
        high_count = sum(1 for f in findings if f["severity"] in {"high", "violation"})
        avg_conf = sum(f["confidence"] for f in findings) / max(len(findings), 1)

        await _save_agent_task(run_id, "classifier", "completed", started,
                                datetime.utcnow().isoformat(), elapsed,
                                {"finding_count": len(findings), "high_severity": high_count})
        await _emit("agent_completed", {
            "agent": "classifier", "finding_count": len(findings),
            "high_count": high_count, "run_id": run_id
        }, run_id)
        return {**state, "findings": findings}
    except Exception as e:
        await _save_agent_task(run_id, "classifier", "failed", started, error_msg=str(e))
        await _emit("agent_failed", {"agent": "classifier", "error": str(e), "run_id": run_id}, run_id)
        return {**state, "findings": [], "error": str(e)}


# ── Node: Redline ─────────────────────────────────────────────────────────────
async def node_redline(state: GraphState) -> GraphState:
    t0 = time.time()
    started = datetime.utcnow().isoformat()
    run_id = state["run_id"]

    await _emit("agent_started", {"agent": "redline", "run_id": run_id}, run_id)

    findings = state.get("findings", [])
    if not findings:
        return {**state, "enriched_findings": []}

    try:
        async with omium_span(state["trace_id"], run_id, "redline", attributes={"phase": "redline", "findings": len(findings)}):
            enriched = await redline_findings(findings)
        elapsed = int((time.time() - t0) * 1000)
        await _save_agent_task(run_id, "redline", "completed", started,
                                datetime.utcnow().isoformat(), elapsed,
                                {"enriched_count": len(enriched)})
        await _emit("agent_completed", {"agent": "redline", "enriched_count": len(enriched), "run_id": run_id}, run_id)
        return {**state, "enriched_findings": enriched}
    except Exception as e:
        await _save_agent_task(run_id, "redline", "failed", started, error_msg=str(e))
        return {**state, "enriched_findings": findings}


# ── Node: Reporter ────────────────────────────────────────────────────────────
async def node_reporter(state: GraphState) -> GraphState:
    t0 = time.time()
    started = datetime.utcnow().isoformat()
    run_id = state["run_id"]
    findings = state.get("enriched_findings") or state.get("findings", [])

    await _emit("agent_started", {"agent": "reporter", "run_id": run_id}, run_id)

    # Save all findings to DB
    await _save_findings(findings)

    # Compute overall confidence
    avg_conf = sum(f["confidence"] for f in findings) / max(len(findings), 1)
    high_count = sum(1 for f in findings if f["severity"] in {"high", "violation"})

    # Update contract status
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE contracts SET status=?, analysed_at=? WHERE id=?",
            ("analysed", datetime.utcnow().isoformat(), state["contract_id"])
        )
        await db.commit()

    # Concurrent outputs: Slack + GitHub PR
    slack_msg = (
        f"*Spectre Analysis Complete* — `{state['contract_name']}`\n"
        f"{len(findings)} findings | {high_count} high/violation | Avg confidence: {avg_conf:.2f}\n"
        f"Run ID: `{run_id}`"
    )

    pr_url = None
    async with aiosqlite.connect(DB_PATH) as db:
        async with omium_span(state["trace_id"], run_id, "reporter", attributes={"phase": "reporting", "findings": len(findings)}):
            slack_task = asyncio.create_task(send_slack(slack_msg, db, run_id=run_id, trace_id=state["trace_id"]))
            pr_task = asyncio.create_task(create_github_pr(state["contract_name"], findings, db, run_id, trace_id=state["trace_id"]))
            await asyncio.gather(slack_task, pr_task, return_exceptions=True)
            pr_url_result = pr_task.result() if not pr_task.exception() else None
            if isinstance(pr_url_result, str):
                pr_url = pr_url_result

    elapsed = int((time.time() - t0) * 1000)
    await _update_run_status(
        run_id, "completed",
        completed_at=datetime.utcnow().isoformat(),
        confidence_score=round(avg_conf, 4),
        runtime_ms=elapsed,
    )
    await _save_agent_task(
        run_id,
        "reporter",
        "completed",
        started,
        datetime.utcnow().isoformat(),
        elapsed,
        {"finding_count": len(findings), "high_count": high_count, "pr_url": pr_url},
    )

    await _emit("workflow_completed", {
        "run_id": run_id,
        "contract_id": state["contract_id"],
        "contract_name": state["contract_name"],
        "finding_count": len(findings),
        "high_count": high_count,
        "avg_confidence": round(avg_conf, 3),
        "pr_url": pr_url,
    }, run_id)

    return {**state, "pr_url": pr_url}


# ── Build LangGraph ───────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("extraction", node_extraction)
    graph.add_node("research", node_research)
    graph.add_node("classifier", node_classifier)
    graph.add_node("redline", node_redline)
    graph.add_node("reporter", node_reporter)

    # Sequential flow (extraction and research run concurrently via asyncio.gather in the runner)
    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "research")
    graph.add_edge("research", "classifier")
    graph.add_edge("classifier", "redline")
    graph.add_edge("redline", "reporter")
    graph.add_edge("reporter", END)

    return graph.compile()


COMPILED_GRAPH = build_graph()


# ── Main runner ───────────────────────────────────────────────────────────────
async def run_pipeline(
    run_id: str,
    contract_id: str,
    contract_name: str,
    file_blob: bytes,
    file_path: str = "",
):
    """
    Entry point called by the API layer.
    Runs the full LangGraph pipeline asynchronously.
    """
    trace_id = run_id
    initial_state: GraphState = {
        "run_id": run_id,
        "contract_id": contract_id,
        "contract_name": contract_name,
        "file_path": file_path,
        "file_blob": file_blob,
        "trace_id": trace_id,
        "clauses": [],
        "regulation_context": {},
        "findings": [],
        "enriched_findings": [],
        "pr_url": None,
        "error": None,
    }

    print(f"[ORCHESTRATOR] Starting pipeline run_id={run_id} trace_id={trace_id}")

    try:
        t0 = time.time()
        await _update_run_status(run_id, "running", started_at=datetime.utcnow().isoformat())

        extraction_result = await node_extraction(initial_state)
        research_result = await node_research(extraction_result)

        merged = {
            **initial_state,
            "clauses": extraction_result.get("clauses", []),
            "regulation_context": research_result.get("regulation_context", {}),
            "error": extraction_result.get("error") or research_result.get("error"),
        }

        if merged.get("error"):
            raise RuntimeError(merged["error"])

        after_classify = await node_classifier(merged)
        after_redline = await node_redline(after_classify)
        await node_reporter(after_redline)

        total_ms = int((time.time() - t0) * 1000)
        print(f"[ORCHESTRATOR] Pipeline completed in {total_ms}ms")

    except Exception as e:
        print(f"[ORCHESTRATOR] Fatal error: {e}")
        await _update_run_status(run_id, "failed", error_msg=str(e))
        await _emit("workflow_failed", {"run_id": run_id, "error": str(e)}, run_id)


def schedule_pipeline(app, run_id: str, contract_id: str, contract_name: str, file_blob: bytes, file_path: str = ""):
    task = asyncio.create_task(run_pipeline(run_id, contract_id, contract_name, file_blob, file_path))
    if not hasattr(app.state, "pipeline_tasks"):
        app.state.pipeline_tasks = {}
    app.state.pipeline_tasks[run_id] = task
    task.add_done_callback(lambda finished: app.state.pipeline_tasks.pop(run_id, None))
    return task
