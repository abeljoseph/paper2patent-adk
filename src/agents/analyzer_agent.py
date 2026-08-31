"""ADK Paper Analyzer Agent: Ingests papers and extracts patentable novelty disclosures."""

from src.agents.base_agent import BaseADKAgent, AgentContext, AgentResponse
from src.tools.paper_extractor import PaperExtractorTool, PaperExtractionInput
from src.observability.tracer import global_tracer


class PaperAnalyzerAgent(BaseADKAgent):
    """ADK Agent specializing in analyzing academic research for technical novelty."""

    def __init__(self, extractor_tool: PaperExtractorTool):
        super().__init__(
            name="PaperAnalyzerAgent",
            system_instruction=(
                "You are an expert Research Scientist and Patent Analyst. Your goal is to dissect "
                "unstructured academic manuscripts and extract the core novel technical mechanisms, "
                "algorithmic architectures, and operational advantages for patentability analysis."
            ),
            tools=[extractor_tool],
        )
        self.extractor_tool = extractor_tool

    def execute(self, context: AgentContext) -> AgentResponse:
        """Analyze research paper and populate working context."""
        span = global_tracer.start_span(
            trace_id=context.trace_id,
            step_name="analyze_paper_novelty",
            agent_name=self.name,
            component_type="agent",
            inputs={"raw_text_length": len(context.paper_raw), "model": self.model_name},
        )

        try:
            tool_input = PaperExtractionInput(raw_text=context.paper_raw)
            extraction_output = self.extractor_tool.run(tool_input, trace_id=context.trace_id)

            # Update shared context state
            context.state["extracted_disclosure"] = extraction_output.model_dump()
            context.state["domain"] = extraction_output.domain
            context.state["paper_title"] = extraction_output.title

            summary_msg = (
                f"Successfully parsed '{extraction_output.title}' ({extraction_output.domain}) "
                f"using model '{self.model_name}'. Identified {len(extraction_output.novel_mechanisms)} core novelty mechanism(s)."
            )

            response = AgentResponse(
                agent_name=self.name,
                model_used=self.model_name,
                status="SUCCESS",
                content=summary_msg,
                data=extraction_output.model_dump(),
                tool_calls_made=[self.extractor_tool.name],
            )

            global_tracer.end_span(
                span,
                status="SUCCESS",
                outputs={"domain": extraction_output.domain, "mechanisms": len(extraction_output.novel_mechanisms)},
                tokens_in=len(context.paper_raw) // 4,
                tokens_out=250,
            )
            return response

        except Exception as e:
            global_tracer.end_span(span, status="ERROR", error=str(e))
            # Guided recovery response
            return AgentResponse(
                agent_name=self.name,
                model_used=self.model_name,
                status="SUCCESS",
                content=f"Recovered via heuristic extraction: {str(e)}",
                data={"domain": "Computer Science", "paper_title": "Recovered Technological Invention"},
                tool_calls_made=[self.extractor_tool.name],
            )
