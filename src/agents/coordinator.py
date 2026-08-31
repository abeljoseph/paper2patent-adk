"""Paper2Patent ADK Coordinator orchestrating multi-agent collaboration and feedback loops."""

import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from src.memory.session_store import SessionMemory
from src.memory.vector_store import VectorMemoryStore
from src.tools.paper_extractor import PaperExtractorTool
from src.tools.prior_art_searcher import PriorArtSearchTool
from src.tools.fto_scorer import FTOScorerTool
from src.tools.claim_drafter import ClaimDrafterTool

from src.agents.base_agent import AgentContext, AgentResponse
from src.agents.analyzer_agent import PaperAnalyzerAgent
from src.agents.examiner_agent import PriorArtExaminerAgent
from src.agents.drafter_agent import PatentClaimDrafterAgent
from src.agents.auditor_agent import IPComplianceAuditorAgent
from src.observability.tracer import global_tracer
from src.observability.metrics import global_metrics, ExecutionMetrics


class PipelineExecutionResult(BaseModel):
    """Complete output package produced by the Paper2Patent ADK multi-agent workflow."""
    trace_id: str
    session_id: str
    paper_title: str
    domain: str
    fto_score: float
    patent_readiness_score: float
    verdict: str
    total_claims_drafted: int
    extracted_disclosure: Dict[str, Any]
    prior_art_analysis: Dict[str, Any]
    fto_report: Dict[str, Any]
    drafted_claims: Dict[str, Any]
    compliance_audit: Dict[str, Any]
    metrics: ExecutionMetrics
    formatted_dossier: str


class Paper2PatentCoordinator:
    """Central ADK Multi-Agent Orchestrator managing sequential execution & iterative refinement."""

    def __init__(self, vector_store: Optional[VectorMemoryStore] = None):
        self.session_memory = SessionMemory()
        self.vector_store = vector_store or VectorMemoryStore()

        # Initialize tools
        self.extractor_tool = PaperExtractorTool()
        self.search_tool = PriorArtSearchTool(vector_store=self.vector_store)
        self.fto_tool = FTOScorerTool()
        self.drafter_tool = ClaimDrafterTool()

        # Initialize sub-agents
        self.analyzer_agent = PaperAnalyzerAgent(self.extractor_tool)
        self.examiner_agent = PriorArtExaminerAgent(self.search_tool, self.fto_tool)
        self.drafter_agent = PatentClaimDrafterAgent(self.drafter_tool)
        self.auditor_agent = IPComplianceAuditorAgent()

    def run_pipeline(
        self,
        paper_text: str,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        max_refinement_cycles: int = 1,
    ) -> PipelineExecutionResult:
        """Run the full end-to-end 4-agent ADK pipeline."""
        session_id = session_id or str(uuid.uuid4())[:8]
        trace_id = trace_id or str(uuid.uuid4())[:8]

        working_memory = self.session_memory.get_or_create_working_memory(session_id)
        working_memory.paper_raw_text = paper_text

        context = AgentContext(
            session_id=session_id,
            trace_id=trace_id,
            paper_raw=paper_text,
            state={},
            iteration=1,
        )

        coordinator_span = global_tracer.start_span(
            trace_id=trace_id,
            step_name="orchestrate_paper2patent_pipeline",
            agent_name="Paper2PatentCoordinator",
            component_type="coordinator",
            inputs={"session_id": session_id, "text_len": len(paper_text)},
        )

        # Stage 1: Paper Novelty Analysis
        resp_analyzer = self.analyzer_agent.execute(context)
        if resp_analyzer.status == "ERROR":
            global_tracer.end_span(coordinator_span, status="ERROR", error="Analyzer failure")
            raise ValueError(f"Paper analysis failed: {resp_analyzer.content}")

        # Stage 2: Prior Art & FTO Collision Examination
        resp_examiner = self.examiner_agent.execute(context)
        if resp_examiner.status == "ERROR":
            global_tracer.end_span(coordinator_span, status="ERROR", error="Examiner failure")
            raise ValueError(f"Prior art examination failed: {resp_examiner.content}")

        # Stage 3: USPTO Claim Drafting
        resp_drafter = self.drafter_agent.execute(context)
        if resp_drafter.status == "ERROR":
            global_tracer.end_span(coordinator_span, status="ERROR", error="Drafter failure")
            raise ValueError(f"Claim drafting failed: {resp_drafter.content}")

        # Stage 4: IP Compliance & Statutory Audit
        resp_auditor = self.auditor_agent.execute(context)
        
        # Check if refinement cycle is triggered
        if resp_auditor.data.get("verdict") == "REFINEMENT_RECOMMENDED" and max_refinement_cycles > 0:
            context.iteration += 1
            # Refine claims with stricter carveout bounds
            resp_drafter = self.drafter_agent.execute(context)
            resp_auditor = self.auditor_agent.execute(context)

        # Finalize coordinator span
        global_tracer.end_span(coordinator_span, status="SUCCESS")

        # Compile telemetry metrics
        spans = global_tracer.get_traces_for_id(trace_id)
        metrics = global_metrics.compute_trace_metrics(spans)

        # Format complete dossier markdown
        dossier = self._generate_dossier_markdown(context, metrics)

        # Sync working memory
        working_memory.extracted_features = context.state.get("extracted_disclosure", {})
        working_memory.prior_art_hits = context.state.get("prior_art_hits", {}).get("top_hits", [])
        working_memory.fto_risk_matrix = context.state.get("fto_report", {})
        working_memory.drafted_claims = context.state.get("drafted_claims", {})
        working_memory.compliance_audit = context.state.get("compliance_audit", {})

        return PipelineExecutionResult(
            trace_id=trace_id,
            session_id=session_id,
            paper_title=context.state.get("paper_title", "Untitled Invention"),
            domain=context.state.get("domain", "Technology"),
            fto_score=context.state.get("fto_report", {}).get("overall_fto_score", 0.0),
            patent_readiness_score=context.state.get("compliance_audit", {}).get("patent_readiness_score", 0.0),
            verdict=context.state.get("compliance_audit", {}).get("verdict", "PENDING"),
            total_claims_drafted=context.state.get("drafted_claims", {}).get("total_claims", 0),
            extracted_disclosure=context.state.get("extracted_disclosure", {}),
            prior_art_analysis=context.state.get("prior_art_hits", {}),
            fto_report=context.state.get("fto_report", {}),
            drafted_claims=context.state.get("drafted_claims", {}),
            compliance_audit=context.state.get("compliance_audit", {}),
            metrics=metrics,
            formatted_dossier=dossier,
        )

    def _generate_dossier_markdown(self, context: AgentContext, metrics: ExecutionMetrics) -> str:
        """Construct full markdown report."""
        title = context.state.get("paper_title", "Invention")
        domain = context.state.get("domain", "Technology")
        fto = context.state.get("fto_report", {})
        drafted = context.state.get("drafted_claims", {})
        audit = context.state.get("compliance_audit", {})

        claims_md = drafted.get("formatted_uspto_document", "")

        return f"""# 📄 Paper2Patent Readiness Dossier

**Invention Title**: {title}  
**Technical Domain**: {domain}  
**Patent Readiness Score**: {audit.get('patent_readiness_score', 0.0) * 100:.1f}%  
**FTO Clearance Score**: {fto.get('overall_fto_score', 0.0) * 100:.1f}%  
**Audit Verdict**: `{audit.get('verdict', 'UNKNOWN')}`  

---

## 🔬 1. Novel Mechanisms & Technical Disclosure
{chr(10).join(f"- **{m.get('name')}**: {m.get('description')}" for m in context.state.get('extracted_disclosure', {}).get('novel_mechanisms', []))}

---

## 🔍 2. Prior Art & Freedom-to-Operate Collision Matrix
- **Risk Category**: {fto.get('risk_category', 'N/A')}
- **Patentability Assessment**: {fto.get('patentability_assessment', 'N/A')}

| Prior Patent | Title | Collision Prob | Risk Level | Recommended Carveout |
| :--- | :--- | :--- | :--- | :--- |
{chr(10).join(f"| `{c.get('patent_number')}` | {c.get('patent_title')} | {c.get('collision_probability', 0)*100:.1f}% | `{c.get('risk_level')}` | {c.get('carveout_strategy')} |" for c in fto.get('collision_items', []))}

---

## ⚖️ 3. USPTO 35 U.S.C. Statutory Compliance Audit
{chr(10).join(f"- **{chk.get('statute')}**: {'✅ PASS' if chk.get('passed') else '⚠️ ATTENTION'} — *{chk.get('detail')}*" for chk in audit.get('statutory_checks', []))}

---

## 📜 4. Formatted Provisional Patent Claims
```text
{claims_md}
```

---

## ⏱️ 5. Agent Orchestration & Observability Telemetry
- **Trace ID**: `{metrics.trace_id}`
- **Total Workflow Latency**: `{metrics.total_duration_ms:.2f} ms`
- **Total Token Volume**: `{metrics.total_tokens}` tokens ({metrics.total_tokens_in} in / {metrics.total_tokens_out} out)
- **Agent Steps Executed**: `{metrics.steps_count}`
"""
