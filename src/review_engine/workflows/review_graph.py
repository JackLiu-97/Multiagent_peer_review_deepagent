from __future__ import annotations

from langgraph.graph import END, StateGraph

from review_engine.core.dimensions import DIMENSION_ORDER
from review_engine.core.settings import Settings
from review_engine.workflows.state import ReviewWorkflowState


def build_review_workflow(runtime, settings: Settings):
    """Create the fixed-dimension LangGraph review workflow."""

    graph = StateGraph(ReviewWorkflowState)

    def initialize_state(state: ReviewWorkflowState) -> ReviewWorkflowState:
        return runtime.initialize_state(state)

    def dispatch_retry(state: ReviewWorkflowState) -> ReviewWorkflowState:
        return runtime.dispatch_retry(state)

    def collect_reviews(state: ReviewWorkflowState) -> ReviewWorkflowState:
        return runtime.collect_reviews(state)

    def critic(state: ReviewWorkflowState) -> ReviewWorkflowState:
        return runtime.run_critic(state)

    def score(state: ReviewWorkflowState) -> ReviewWorkflowState:
        return runtime.score_paper(state)

    def formatter(state: ReviewWorkflowState) -> ReviewWorkflowState:
        return runtime.format_report(state)

    def export_result(state: ReviewWorkflowState) -> ReviewWorkflowState:
        return runtime.export_result(state)

    graph.add_node("initialize_state", initialize_state)
    graph.add_node("dispatch_retry", dispatch_retry)
    for dimension in DIMENSION_ORDER:
        graph.add_node(
            f"review_{dimension}",
            lambda state, dimension_key=dimension: runtime.review_dimension(state, dimension_key),
        )
    graph.add_node("collect_reviews", collect_reviews)
    graph.add_node("critic", critic)
    graph.add_node("score", score)
    graph.add_node("formatter", formatter)
    graph.add_node("export_result", export_result)

    graph.set_entry_point("initialize_state")
    graph.add_edge("initialize_state", "dispatch_retry")

    for dimension in DIMENSION_ORDER:
        graph.add_edge("dispatch_retry", f"review_{dimension}")
        graph.add_edge(f"review_{dimension}", "collect_reviews")

    graph.add_edge("collect_reviews", "critic")

    def route_after_critic(state: ReviewWorkflowState) -> str:
        critic_result = state.get("critic_result") or {}
        if critic_result.get("approved", False):
            return "score"
        if int(state.get("current_round", 1)) >= int(settings.max_review_rounds):
            return "score"
        return "dispatch_retry"

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "dispatch_retry": "dispatch_retry",
            "score": "score",
        },
    )
    graph.add_edge("score", "formatter")
    graph.add_edge("formatter", "export_result")
    graph.add_edge("export_result", END)
    return graph.compile()
