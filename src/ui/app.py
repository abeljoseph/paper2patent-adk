"""Streamlit Web Dashboard for Paper2Patent Google ADK Agent with HITL & Model Routing."""

import json
import streamlit as st
from src.agents.coordinator import Paper2PatentCoordinator
from src.eval.benchmark import GoldenDatasetEvaluator
from src.observability.tracer import global_tracer
from src.observability.metrics import global_metrics

# Page configuration
st.set_page_config(
    page_title="Paper2Patent - Google ADK Agent",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1a73e8;
    }
    .badge-clean { background-color: #e6f4ea; color: #137333; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-caution { background-color: #fef7e0; color: #b06000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-blocked { background-color: #fce8e6; color: #c5221f; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

SAMPLE_PAPERS = {
    "AI: State-Space Sequence Modeling (Deep Learning)": """# Sub-Quadratic State-Space Memory Recurrence for Real-Time Sequence Processing

## Abstract
Modern deep neural networks rely heavily on multi-head scaled dot-product attention, which exhibits quadratic O(N^2) memory and compute bottlenecks with sequence length. In this work, we propose 'Selective Structured Recurrence' (SSR), an adaptive continuous-time state-space operator that dynamically modulates gating matrices based on input context. 

## Novel Technical Mechanism
Our primary contribution is a context-dependent state matrix operator B(t) and C(t) combined with a discrete associative scan algorithm. Unlike static convolution filters, the SSR engine filters irrelevant tokens with linear O(N) memory complexity and 3.2x throughput speedup over baseline Transformers on 128k context windows.
""",
    "Quantum: Superconducting Flux Qubit Controller": """# Real-Time Cryogenic Pulse Modulation for Superconducting Qubit Error Mitigation

## Abstract
Quantum processors suffer from phase decoherence and cross-talk during multi-qubit gate operations. We introduce a Cryogenic Pulse Modulation (CPM) controller operating at 20mK that dynamically corrects flux drift in transmon qubit arrays.

## Novel Technical Mechanism
The invention comprises an on-chip Josephson arbitrary waveform generator coupled to an active feedback loop that suppresses thermal drift and reduces gate infidelity to below 0.05% per Clifford operation.
""",
    "Biotech: Engineered CRISPR Cas12a Activator": """# Engineered Cas12a Ribonucleoprotein for Multiplexed Gene Activation

## Abstract
Traditional CRISPR dCas9 transcriptional activators exhibit high off-target binding and large molecular footprint. We present an engineered Cas12a variant with a synthetic tripartite activation domain (VPR-mini).

## Novel Technical Mechanism
The novel fusion complex recognizes an expanded 5'-TTTV-3' PAM motif with 4.5x higher transcriptional upregulation efficiency in human embryonic kidney cells while reducing non-specific genomic cuts to undetectable levels.
""",
}


def main():
    st.title("📜 Paper2Patent: Google ADK Patent Agent")
    st.caption("Autonomous Academic Research to USPTO Prior-Art, FTO Clearance & Patent Claims")

    # Sidebar
    st.sidebar.header("⚙️ Configuration")
    sample_choice = st.sidebar.selectbox("Load Sample Research Paper", list(SAMPLE_PAPERS.keys()))
    enable_hitl = st.sidebar.checkbox("Enable Human-in-the-Loop (HITL) Gate", value=False)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Strategic Model Routing**:")
    st.sidebar.markdown("• Extraction: `gemini-2.0-flash`")
    st.sidebar.markdown("• FTO Search: `gemini-2.0-flash`")
    st.sidebar.markdown("• Claim Drafter: `gemini-2.5-pro`")
    st.sidebar.markdown("• Statutory Auditor: `gemini-2.5-pro`")
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Storage**: Persistent SQLite DB")
    st.sidebar.markdown("**Observability**: OpenTelemetry SDK + PII Scrubber")

    # Paper Input
    paper_input = st.text_area(
        "Enter Academic Paper Text / Abstract / Disclosures:",
        value=SAMPLE_PAPERS[sample_choice],
        height=220,
    )

    coordinator = Paper2PatentCoordinator()

    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        if st.button("🚀 Run Multi-Agent ADK Pipeline", type="primary", use_container_width=True):
            with st.spinner("Executing Google ADK Multi-Agent Orchestration..."):
                result = coordinator.run_pipeline(paper_text=paper_input, require_human_approval=enable_hitl)
                st.session_state["pipeline_result"] = result

    with col_btn2:
        if st.button("🧪 Run Golden Benchmark", use_container_width=True):
            with st.spinner("Evaluating regression benchmark across Golden Dataset..."):
                evaluator = GoldenDatasetEvaluator()
                st.session_state["benchmark_summary"] = evaluator.run_benchmark()

    # Benchmark display if available
    if "benchmark_summary" in st.session_state:
        b = st.session_state["benchmark_summary"]
        st.success(f"🎯 Golden Dataset Benchmark Completed: {b.passed_cases}/{b.total_test_cases} Cases Passed ({b.overall_pass_rate*100:.1f}%)")
        bcol1, bcol2, bcol3, bcol4 = st.columns(4)
        with bcol1:
            st.metric("Domain Accuracy", f"{b.domain_classification_accuracy*100:.0f}%")
        with bcol2:
            st.metric("Claim Compliance", f"{b.claim_count_compliance_rate*100:.0f}%")
        with bcol3:
            st.metric("FTO Range Match", f"{b.fto_range_compliance_rate*100:.0f}%")
        with bcol4:
            st.metric("Statutory Match", f"{b.statutory_verdict_match_rate*100:.0f}%")

    # Display Results if available
    if "pipeline_result" in st.session_state:
        res = st.session_state["pipeline_result"]

        st.markdown("---")

        if res.status == "PAUSED_FOR_HUMAN_APPROVAL":
            st.warning("⚠️ **Human-in-the-Loop Checkpoint**: Pipeline paused after Stage 2. Please review FTO Collision Matrix below before proceeding to Claim Drafting.")
            feedback = st.text_input("Optional Attorney Feedback / Claim Limitation:", placeholder="e.g. Limit claim 1 to continuous-time recurrence operators")
            
            if st.button("✅ Approve Carveouts & Synthesize USPTO Claims", type="primary"):
                with st.spinner("Resuming Pipeline with Pro-Tier Reasoning..."):
                    res = coordinator.resume_pipeline(session_id=res.session_id, human_approved=True, human_feedback=feedback)
                    st.session_state["pipeline_result"] = res
                    st.rerun()

        # Scoreboard
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Technical Domain", res.domain)
        with col2:
            st.metric("FTO Clearance Score", f"{res.fto_score*100:.1f}%")
        with col3:
            st.metric("Patent Readiness Score", f"{res.patent_readiness_score*100:.1f}%")
        with col4:
            st.metric("Audit Verdict", res.verdict)

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "🔬 1. Novelty & Extraction",
            "🔍 2. Prior Art & FTO Collision",
            "📜 3. USPTO Patent Claims",
            "📊 4. Observability & Traces",
        ])

        with tab1:
            st.subheader(f"Extracted Disclosure: {res.paper_title}")
            st.markdown(f"**Abstract Summary**: {res.extracted_disclosure.get('abstract_summary', '')}")
            
            st.markdown("#### Novel Mechanisms Identified:")
            for mech in res.extracted_disclosure.get("novel_mechanisms", []):
                with st.expander(f"🔹 {mech.get('name')}", expanded=True):
                    st.write(f"**Description**: {mech.get('description')}")
                    st.write(f"**Technical Advantage**: {mech.get('technical_advantage')}")

        with tab2:
            st.subheader("Prior Art Citations & Freedom-to-Operate (FTO) Matrix")
            st.info(f"**Patentability Assessment**: {res.fto_report.get('patentability_assessment')}")
            
            collision_items = res.fto_report.get("collision_items", [])
            if collision_items:
                st.table([
                    {
                        "Patent Number": c["patent_number"],
                        "Title": c["patent_title"],
                        "Collision Probability": f"{c['collision_probability']*100:.1f}%",
                        "Risk Level": c["risk_level"],
                        "Carveout Strategy": c["carveout_strategy"],
                    }
                    for c in collision_items
                ])

        with tab3:
            st.subheader("USPTO Provisional Patent Claims")
            st.caption("Drafted strictly adhering to 35 U.S.C. 112 MPEP claim formatting rules via Gemini 2.5 Pro.")
            
            if res.drafted_claims.get("claims"):
                for claim in res.drafted_claims.get("claims", []):
                    with st.container():
                        st.markdown(f"**Claim {claim['claim_number']} ({claim['claim_type']})**")
                        st.code(claim["full_claim_text"], language="text")

                st.download_button(
                    label="📥 Download Full Patent Readiness Dossier (.md)",
                    data=res.formatted_dossier,
                    file_name=f"patent_dossier_{res.trace_id}.md",
                    mime="text/markdown",
                )
            else:
                st.info("Claims will appear once Stage 2 is approved.")

        with tab4:
            st.subheader("OpenTelemetry & Google ADK Agent Tracing")
            st.write(f"**Trace ID**: `{res.metrics.trace_id}`")
            
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.metric("Total Latency", f"{res.metrics.total_duration_ms:.2f} ms")
            with mcol2:
                st.metric("Total Token Consumption", f"{res.metrics.total_tokens} tokens")
            with mcol3:
                st.metric("Executed Agent Steps", res.metrics.steps_count)

            st.markdown("#### Strategic Model Routing Table:")
            st.json(res.model_routing)

            st.markdown("#### Agent Latency Breakdown:")
            st.json(res.metrics.agent_breakdown)

            st.markdown("#### Full OpenTelemetry Spans (PII Scrubbed):")
            spans = global_tracer.get_traces_for_id(res.trace_id)
            st.json([s.model_dump() for s in spans])


if __name__ == "__main__":
    main()
