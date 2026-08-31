"""ADK Patent Claim Drafter Agent: Synthesizes USPTO-compliant patent claims."""

from src.agents.base_agent import BaseADKAgent, AgentContext, AgentResponse
from src.tools.claim_drafter import ClaimDrafterTool, ClaimDraftingInput
from src.observability.tracer import global_tracer


class PatentClaimDrafterAgent(BaseADKAgent):
    """ADK Agent functioning as a Registered Patent Attorney drafting provisional claims."""

    def __init__(self, drafter_tool: ClaimDrafterTool):
        super().__init__(
            name="PatentClaimDrafterAgent",
            system_instruction=(
                "You are a licensed Patent Attorney. Your mission is to draft rigorous, defensible, "
                "and enforceable patent claims adhering to 35 U.S.C. 112 requirements, maximizing "
                "broad commercial coverage while cleanly steering around prior art citations."
            ),
            tools=[drafter_tool],
        )
        self.drafter_tool = drafter_tool

    def execute(self, context: AgentContext) -> AgentResponse:
        """Draft independent and dependent patent claims."""
        span = global_tracer.start_span(
            trace_id=context.trace_id,
            step_name="draft_patent_claims",
            agent_name=self.name,
            component_type="agent",
            inputs={"iteration": context.iteration},
        )

        try:
            extracted = context.state.get("extracted_disclosure", {})
            mechanisms = [m["name"] for m in extracted.get("novel_mechanisms", [])]
            carveouts = context.state.get("carveout_strategies", [])

            draft_input = ClaimDraftingInput(
                paper_title=context.state.get("paper_title", "Novel System and Method"),
                domain=context.state.get("domain", "Computer Science"),
                novel_mechanisms=mechanisms,
                fto_carveouts=carveouts,
                num_claims=5,
            )

            draft_output = self.drafter_tool.run(draft_input, trace_id=context.trace_id)

            # Update shared context state
            context.state["drafted_claims"] = draft_output.model_dump()

            summary = (
                f"Generated {draft_output.total_claims} USPTO claims "
                f"({draft_output.independent_claim_count} Independent, {draft_output.dependent_claim_count} Dependent) "
                f"with {draft_output.statutory_compliance_score * 100:.0f}% statutory compliance rating."
            )

            response = AgentResponse(
                agent_name=self.name,
                status="SUCCESS",
                content=summary,
                data=draft_output.model_dump(),
                tool_calls_made=[self.drafter_tool.name],
            )

            global_tracer.end_span(
                span,
                status="SUCCESS",
                outputs={"claims_count": draft_output.total_claims, "compliance": draft_output.statutory_compliance_score},
                tokens_in=450,
                tokens_out=600,
            )
            return response

        except Exception as e:
            global_tracer.end_span(span, status="ERROR", error=str(e))
            return AgentResponse(
                agent_name=self.name,
                status="ERROR",
                content=f"Claim drafting failed: {str(e)}",
                tool_calls_made=[self.drafter_tool.name],
            )
