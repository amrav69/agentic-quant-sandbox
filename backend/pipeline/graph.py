"""LangGraph feedback-loop pipeline for the Agentic Quant Sandbox.

Flow
----
ResearchNode → CodeGenNode → ExecuteNode → CriticNode → DecisionNode
                    ↑                                         |
                    └─────── RetryCodeGen ←─── FAIL (iter<1) ─┘
                                                              |
                                              PASS or FAIL (iter>=1) → END

Maximum 2 total attempts (iteration 0 and 1).
"""

from __future__ import annotations

import logging
import os
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from backend.agents.codegen_agent import CodeGenAgent
from backend.agents.critic_agent import CriticAgent
from backend.agents.research_agent import ResearchAgent
from backend.execution.executor import execute_backtest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class PipelineState(TypedDict):
    """Shared mutable state threaded through every graph node."""

    # Input
    symbol: str
    request_data: dict  # raw CritiqueRequest payload

    # Research output (set once, never overwritten)
    research: dict

    # Intermediate per-step outputs (overwritten each iteration)
    _codegen_result: dict
    _execution_result: dict
    _critique_result: dict

    # Loop counters
    iteration: int       # 0-based; maximum value = 1
    iterations: list     # list of per-attempt dicts

    # Final outputs (set by decision node)
    final_verdict: str
    final_execution_result: dict
    final_critique: dict


# ---------------------------------------------------------------------------
# Sentinel for "not yet set" dicts/strings
# ---------------------------------------------------------------------------

_EMPTY: dict = {}


# ---------------------------------------------------------------------------
# Agent singletons (lazy, created once per graph invocation context)
# ---------------------------------------------------------------------------

def _make_agents() -> dict:
    return {
        "research": ResearchAgent(),
        "codegen": CodeGenAgent(),
        "critic": CriticAgent(),
    }


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


async def research_node(state: PipelineState) -> dict:
    """Run the ResearchAgent and store output in state."""
    agents = _make_agents()
    logger.info("pipeline:research_node — running for symbol=%s", state.get("symbol"))
    research_result = await agents["research"].analyze(state["request_data"])
    return {"research": research_result}


async def codegen_node(state: PipelineState) -> dict:
    """Run the CodeGenAgent. On retry, injects fatal/serious issues as context."""
    agents = _make_agents()
    research = state["research"]
    iteration = state.get("iteration", 0)

    if iteration == 0:
        # First attempt — standard generate
        logger.info("pipeline:codegen_node — first attempt")
        codegen_result = await agents["codegen"].generate(research)
    else:
        # Retry — extract only fatal + serious issues from the last attempt
        logger.info("pipeline:codegen_node — retry (iteration=%d)", iteration)
        last_attempt = state["iterations"][-1]
        last_critique = last_attempt.get("critique", {})
        all_issues = last_critique.get("issues", [])

        actionable = [
            i for i in all_issues
            if isinstance(i, dict) and i.get("severity") in ("fatal", "serious")
        ]
        issue_lines = "\n".join(
            f"{idx + 1}. [{i['severity'].upper()}] {i['issue']}"
            for idx, i in enumerate(actionable)
        ) or "No specific issues captured."

        # Build retry prompt by injecting context into the research output copy
        research_with_context = dict(research)
        original_analysis = research.get("analysis", "")
        research_with_context["analysis"] = (
            f"REVISION REQUIRED — Previous attempt failed.\n\n"
            f"Fix the following issues:\n{issue_lines}\n\n"
            f"Original hypothesis:\n{original_analysis}"
        )
        codegen_result = await agents["codegen"].generate(research_with_context)

    return {"_codegen_result": codegen_result}


async def execute_node(state: PipelineState) -> dict:
    """Run the sandboxed executor on the code produced by the last CodeGen call."""
    codegen_result = state.get("_codegen_result", {})
    code = codegen_result.get("code", "")
    timeout = int(os.getenv("EXECUTOR_TIMEOUT_SECONDS", 30))

    logger.info("pipeline:execute_node — executing code (len=%d)", len(code))
    execution_result = await execute_backtest(code, timeout=timeout)
    return {"_execution_result": execution_result.model_dump()}


async def critic_node(state: PipelineState) -> dict:
    """Run the CriticAgent against the latest code + execution result."""
    agents = _make_agents()
    research = state["research"]
    codegen_result = state.get("_codegen_result", {})
    execution_result_dict = state.get("_execution_result", {})

    logger.info("pipeline:critic_node — running critique")
    critique_result = await agents["critic"].critique(
        {
            "research_analysis": research,
            "generated_code": codegen_result,
        },
        execution_result=execution_result_dict,
    )
    return {"_critique_result": critique_result}


def decision_node(state: PipelineState) -> dict:
    """Record the current attempt and decide: PASS→END, FAIL→retry or END."""
    iteration = state.get("iteration", 0)
    codegen_result = state.get("_codegen_result", {})
    execution_result_dict = state.get("_execution_result", {})
    critique_result = state.get("_critique_result", {})

    attempt_record = {
        "iteration": iteration + 1,          # 1-based for display
        "code": codegen_result.get("code", ""),
        "execution_result": execution_result_dict,
        "critique": critique_result,
    }

    existing_iterations = list(state.get("iterations", []))
    existing_iterations.append(attempt_record)

    verdict = critique_result.get("verdict", "FAIL")
    logger.info(
        "pipeline:decision_node — iteration=%d verdict=%s", iteration, verdict
    )

    updates: dict[str, Any] = {
        "iterations": existing_iterations,
        "iteration": iteration + 1,
        "final_verdict": verdict,
        "final_execution_result": execution_result_dict,
        "final_critique": critique_result,
    }
    return updates


def _route_decision(state: PipelineState) -> str:
    """Conditional edge: decide next node after DecisionNode."""
    verdict = state.get("final_verdict", "FAIL")
    iteration = state.get("iteration", 1)  # already incremented by decision_node

    if verdict == "PASS":
        logger.info("pipeline:route — PASS → END")
        return END
    if iteration >= 2:
        logger.info("pipeline:route — FAIL after %d iterations → END", iteration)
        return END
    logger.info("pipeline:route — FAIL (iteration=%d < 2) → retry_codegen", iteration)
    return "retry_codegen"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_pipeline_graph() -> Any:
    """Construct and compile the LangGraph StateGraph for the critique pipeline."""
    graph = StateGraph(PipelineState)

    # Nodes
    graph.add_node("research", research_node)
    graph.add_node("codegen", codegen_node)
    graph.add_node("execute", execute_node)
    graph.add_node("critic", critic_node)
    graph.add_node("decision", decision_node)

    # Retry branch re-uses the same codegen/execute/critic nodes under a
    # different alias so we can distinguish them in the edge definitions.
    graph.add_node("retry_codegen", codegen_node)
    graph.add_node("retry_execute", execute_node)
    graph.add_node("retry_critic", critic_node)
    graph.add_node("retry_decision", decision_node)

    # Entry point
    graph.set_entry_point("research")

    # First-attempt edges
    graph.add_edge("research", "codegen")
    graph.add_edge("codegen", "execute")
    graph.add_edge("execute", "critic")
    graph.add_edge("critic", "decision")

    # Decision → conditional branch
    graph.add_conditional_edges(
        "decision",
        _route_decision,
        {
            "retry_codegen": "retry_codegen",
            END: END,
        },
    )

    # Retry-attempt edges
    graph.add_edge("retry_codegen", "retry_execute")
    graph.add_edge("retry_execute", "retry_critic")
    graph.add_edge("retry_critic", "retry_decision")

    # Final decision always ends
    graph.add_edge("retry_decision", END)

    return graph.compile()


# Module-level compiled graph (created once on import)
pipeline_graph = build_pipeline_graph()


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


async def run_critique_pipeline(request_data: dict) -> dict:
    """Run the full LangGraph critique pipeline for a given request payload.

    Parameters
    ----------
    request_data : dict
        Serialized CritiqueRequest fields (symbol, price, rsi, …).

    Returns
    -------
    dict
        Pipeline result with keys:
        ``research_analysis``, ``iterations``, ``final_verdict``,
        ``final_execution_result``, ``final_critique``, ``total_iterations``.
    """
    symbol = request_data.get("symbol", "UNKNOWN")
    logger.info("run_critique_pipeline: starting for symbol=%s", symbol)

    initial_state: PipelineState = {
        "symbol": symbol,
        "request_data": request_data,
        "research": {},
        "_codegen_result": {},
        "_execution_result": {},
        "_critique_result": {},
        "iteration": 0,
        "iterations": [],
        "final_verdict": "FAIL",
        "final_execution_result": {},
        "final_critique": {},
    }

    # Build a fresh graph each call so that any test patches to agent methods
    # are picked up correctly (module-level compiled graphs close over stale
    # function references before patches are applied).
    graph = build_pipeline_graph()
    final_state = await graph.ainvoke(initial_state)

    iterations = final_state.get("iterations", [])
    research = final_state.get("research", {})

    # Surface first-attempt generated_code for backward-compat callers
    first_code = iterations[0]["code"] if iterations else ""
    first_execution = iterations[0]["execution_result"] if iterations else {}
    first_critique = iterations[0]["critique"] if iterations else {}

    return {
        # Backward-compatible top-level fields
        "research_analysis": research,
        "generated_code": {"agent": "codegen", "code": first_code},
        "execution_result": first_execution,
        "critique": first_critique,
        # New fields
        "iterations": iterations,
        "final_verdict": final_state.get("final_verdict", "FAIL"),
        "final_execution_result": final_state.get("final_execution_result", {}),
        "final_critique": final_state.get("final_critique", {}),
        "total_iterations": len(iterations),
    }
