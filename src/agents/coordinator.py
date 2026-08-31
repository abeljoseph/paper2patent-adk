"""Paper2Patent ADK Coordinator orchestrating multi-agent collaboration, HITL gates, and async execution."""

import uuid
import asyncio
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
from src.agents.router import ModelRouter
from src.observability.tracer import global_tracer
from src.observability.metrics import global_metrics, ExecutionMetrics


class PipelineExecutionResult(BaseModel):
    """Complete output package produced by the Paper2Patent ADK multi-agent workflow."""
    trace_id: str
    session_id: str
    status: str = "COMPLETED"  # COMPLETED, PAUSED_FOR_HUMAN_APPROVAL, ERROR
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
    model_routing: Dict[str, str] = Field(default_factory=dict)
    metrics: ExecutionMetrics
    formatted_dossier: str


class Paper2PatentCoordinator:
    """Central ADK Multi-Agent Orchestrator managing model routing, HITL approval, and SQLite persistence."""

    def __init__(self, vector_store: Optional[VectorMemoryStore] = None, session_memory: Optional[SessionMemory] = None):
        self.session_memory = session_memory or SessionMemory()
        self.vector_store = vector_store or VectorMemoryStore()

        # Initialize tools
        self.extractor_tool = PaperExtractorTool()
        self.search_tool = PriorArtSearchTool(vector_store=self.vector_store)
        self.fto_tool = FTOScorerTool()
        self.drafter_tool = ClaimDrafterTool()

        # Initialize sub-agents with strategic model routing
        self.analyzer_agent = PaperAnalyzerAgent(self.extractor_tool)
        self.examiner_agent = PriorArtExaminerAgent(self.search_tool, self.fto_tool)
        self.drafter_agent = PatentClaimDrafterAgent(self.drafter_tool)
        self.auditor_agent = IPComplianceAuditorAgent()

        # Context cache for paused HITL runs
        self._active_contexts: Dict[str, AgentContext] = {}

    def run_pipeline(
        self,
        paper_text: str,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        require_human_approval: bool = False,
        max_refinement_cycles: int = 1,
    ) -> PipelineExecutionResult:
        """Run the end-to-end 4-agent ADK pipeline with optional Human-in-the-Loop checkpoints."""
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
            requires_human_approval=require_human_approval,
            human_approved=False,
        )

        coordinator_span = global_tracer.start_span(
            trace_id=trace_id,
            step_name="orchestrate_paper2patent_pipeline",
            agent_name="Paper2PatentCoordinator",
            component_type="coordinator",
            inputs={"session_id": session_id, "text_len": len(paper_text), "hitl": require_human_approval},
        )

        # Record initial user message in persistent SQLite session memory
        self.session_memory.add_message(session_id, "user", f"Analyze research paper: {paper_text[:200]}...")

        # Stage 1: Paper Novelty Analysis (gemini-2.0-flash)
        self.analyzer_agent.execute(context)

        # Stage 2: Prior Art & FTO Collision Examination (gemini-2.0-flash)
        resp_examiner = self.examiner_agent.execute(context)

        # Check Human-in-the-Loop checkpoint
        if require_human_approval and resp_examiner.status == "PAUSED_FOR_HUMAN_APPROVAL":
            self._active_contexts[session_id] = context
            global_tracer.end_span(coordinator_span, status="PAUSED_FOR_HUMAN_APPROVAL")
            spans = global_tracer.get_traces_for_id(trace_id)
            metrics = global_metrics.compute_trace_metrics(spans)

            return PipelineExecutionResult(
                trace_id=trace_id,
                session_id=session_id,
                status="PAUSED_FOR_HUMAN_APPROVAL",
                paper_title=context.state.get("paper_title", "Untitled Invention"),
                domain=context.state.get("domain", "Technology"),
                fto_score=context.state.get("fto_report", {}).get("overall_fto_score", 0.0),
                patent_readiness_score=0.0,
                verdict="PAUSED_FOR_ATTORNEY_APPROVAL",
                total_claims_drafted=0,
                extracted_disclosure=context.state.get("extracted_disclosure", {}),
                prior_art_analysis=context.state.get("prior_art_hits", {}),
                fto_report=context.state.get("fto_report", {}),
                drafted_claims={},
                compliance_audit={},
                model_routing=ModelRouter.get_routing_manifest(),
                metrics=metrics,
                formatted_dossier="*Pipeline paused at Stage 2 for Human Patent Attorney review of FTO collision carveouts.*",
            )

        # Continue to Stage 3 & 4
        return self._finish_stages_after_approval(context, coordinator_span, max_refinement_cycles)

    def resume_pipeline(
        self,
        session_id: str,
        human_approved: bool = True,
        human_feedback: Optional[str] = None,
        max_refinement_cycles: int = 1,
    ) -> PipelineExecutionResult:
        """Resume execution of a pipeline paused at Human-in-the-Loop checkpoint."""
        context = self._active_contexts.get(session_id)
        if not context:
            # Reconstruct from persistent SQLite memory
            working = self.session_memory.get_or_create_working_memory(session_id)
            context = AgentContext(
                session_id=session_id,
                trace_id=str(uuid.uuid4())[:8],
                paper_raw=working.paper_raw_text or "",
                state={
                    "extracted_disclosure": working.extracted_features,
                    "prior_art_hits": {"top_hits": working.prior_art_hits},
                    "fto_report": working.fto_risk_matrix,
                    "domain": working.extracted_features.get("domain", "Technology"),
                    "paper_title": working.extracted_features.get("title", "Invention"),
                },
                iteration=working.current_iteration,
            )

        context.human_approved = human_approved
        context.human_feedback = human_feedback

        resume_span = global_tracer.start_span(
            trace_id=context.trace_id,
            step_name="resume_after_human_approval",
            agent_name="Paper2PatentCoordinator",
            component_type="coordinator",
            inputs={"session_id": session_id, "approved": human_approved, "feedback": human_feedback or "None"},
        )

        return self._finish_stages_after_approval(context, resume_span, max_refinement_cycles)

    def _finish_stages_after_approval(
        self,
        context: AgentContext,
        coordinator_span: Any,
        max_refinement_cycles: int = 1,
    ) -> PipelineExecutionResult:
        """Complete Stages 3 (Drafter - Pro) & 4 (Auditor - Pro)."""
        # Stage 3: USPTO Claim Drafting (gemini-2.5-pro)
        self.drafter_agent.execute(context)

        # Stage 4: IP Compliance & Statutory Audit (gemini-2.5-pro)
        resp_auditor = self.auditor_agent.execute(context)

        # Statutory Refinement Loop if verdict is not clean
        if resp_auditor.data.get("verdict") == "REFINEMENT_RECOMMENDED" and max_refinement_cycles > 0:
            context.iteration += 1
            self.drafter_agent.execute(context)
            self.auditor_agent.execute(context)

        global_tracer.end_span(coordinator_span, status="SUCCESS")

        spans = global_tracer.get_traces_for_id(context.trace_id)
        metrics = global_metrics.compute_trace_metrics(spans)
        dossier = self._generate_dossier_markdown(context, metrics)

        # Update SQLite persistent working memory
        working_memory = self.session_memory.get_or_create_working_memory(context.session_id)
        working_memory.extracted_features = context.state.get("extracted_disclosure", {})
        working_memory.prior_art_hits = context.state.get("prior_art_hits", {}).get("top_hits", [])
        working_memory.fto_risk_matrix = context.state.get("fto_report", {})
        working_memory.drafted_claims = context.state.get("drafted_claims", {})
        working_memory.compliance_audit = context.state.get("compliance_audit", {})
        self.session_memory.save_working_memory(working_memory)

        # Record assistant completion in session memory
        self.session_memory.add_message(
            context.session_id,
            "assistant",
            f"Drafted {len(context.state.get('drafted_claims', {}).get('claims', []))} claims. Verdict: {context.state.get('compliance_audit', {}).get('verdict')}",
        )

        return PipelineExecutionResult(
            trace_id=context.trace_id,
            session_id=context.session_id,
            status="COMPLETED",
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
            model_routing=ModelRouter.get_routing_manifest(),
            metrics=metrics,
            formatted_dossier=dossier,
        )

    async def run_pipeline_async(
        self,
        paper_text: str,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        require_human_approval: bool = False,
        max_refinement_cycles: int = 1,
    ) -> PipelineExecutionResult:
        """Asynchronous non-blocking pipeline execution."""
        return await asyncio.to_thread(
            self.run_pipeline,
            paper_text,
            session_id,
            trace_id,
            require_human_approval,
            max_refinement_cycles,
        )

    def _generate_dossier_markdown(self, context: AgentContext, metrics: ExecutionMetrics) -> str:
        """Construct full markdown report."""
        title = context.state.get("paper_title", "Invention")
        domain = context.state.get("domain", "Technology")
        fto = context.state.get("fto_report", {})
        drafted = context.state.get("drafted_claims", {})
        audit = context.state.get("compliance_audit", {})
        routing = ModelRouter.get_routing_manifest()

        claims_md = drafted.get("formatted_uspto_document", "")

        return f"""# 📄 Paper2Patent Readiness Dossier

**Invention Title**: {title}  
**Technical Domain**: {domain}  
**Patent Readiness Score**: {audit.get('patent_readiness_score', 0.0) * 100:.1f}%  
**FTO Clearance Score**: {fto.get('overall_fto_score', 0.0) * 100:.1f}%  
**Audit Verdict**: `{audit.get('verdict', 'UNKNOWN')}`  

---

## 🧭 Strategic Model Routing Matrix
- **Extraction Tier**: `{routing.get('PaperAnalyzerAgent')}` (Flash)
- **Prior Art & FTO Tier**: `{routing.get('PriorArtExaminerAgent')}` (Flash)
- **Claim Drafting Tier**: `{routing.get('PatentClaimDrafterAgent')}` (Pro Reasoning)
- **35 U.S.C. Legal Audit Tier**: `{routing.get('IPComplianceAuditorAgent')}` (Pro Reasoning)

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
