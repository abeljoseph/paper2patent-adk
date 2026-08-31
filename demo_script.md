# 🎬 Paper2Patent — 2-Minute Video Demonstration Script

**Project Name**: Paper2Patent (Google ADK Autonomous Prior-Art & Patent Claim Agent)  
**Target Evaluator**: Google FDE Project Evaluator / Agent Assessor  
**Target Duration**: ~120 Seconds (2 Minutes)  
**Language**: English  

---

## ⏱️ Video Breakdown & Narration

### **0:00 – 0:25 | The Problem & The Mission**
* **On-Screen**: Title Slide / Architecture Diagram showing Google ADK Multi-Agent Flow.
* **Speaker**:
  > *"Every year, academic researchers and R&D engineers publish thousands of breakthrough discoveries on arXiv and in journals, but miss out on patenting their IP because manual prior-art search and claim drafting costs tens of thousands of dollars and takes weeks.*  
  > *Meet **Paper2Patent** — an autonomous multi-agent system built with the **Google Agent Development Kit (ADK)** that transforms raw scientific papers into rejection-proof, USPTO-compliant provisional patent filings in seconds."*

---

### **0:25 – 0:55 | Google ADK Architecture & 5-Pillar Overview**
* **On-Screen**: Screen recording transitioning from Terminal CLI to the Streamlit UI dashboard.
* **Speaker**:
  > *"Paper2Patent coordinates four specialized ADK agents:  
  > 1. The **Paper Analyzer Agent** extracts core novelty mechanisms and equations using typed Pydantic tools.  
  > 2. The **Prior Art Examiner Agent** searches semantic vector memory over global patent databases and computes a mathematical Freedom-to-Operate clearance score.  
  > 3. The **Patent Claim Drafter Agent** synthesizes USPTO MPEP-compliant independent and dependent claims.  
  > 4. And the **IP Compliance Auditor Agent** validates the claims against 35 U.S.C. statutes 101, 102, 103, and 112 with an automated refinement loop."*

---

### **0:55 – 1:35 | Live Demonstration & Multi-Agent Execution**
* **On-Screen**: In the Streamlit UI, select the *State-Space Sequence Modeling* paper and click **Run Multi-Agent ADK Pipeline**. Show the live outputs in each tab:
  - Tab 1: Extracted novelty mechanisms.
  - Tab 2: Freedom-to-Operate collision table and carveout recommendations.
  - Tab 3: Generated USPTO provisional claim specification.
  - Tab 4: OpenTelemetry tracing logs, token counters, and latency waterfall.
* **Speaker**:
  > *"Watch it in action. When we submit an academic paper on sub-quadratic state-space recurrence, our ADK pipeline runs in real-time.  
  > The Examiner agent identifies relevant prior art from Google and IBM patents, flags a moderate collision, and computes a 78% FTO score.  
  > The Drafter Agent creates formal independent system and method claims that surgically carve out daylight from existing patents.  
  > Finally, in the Observability tab, our OpenTelemetry tracer logs every agent thought, tool execution, and token metric with full trace provenance."*

---

### **1:35 – 2:00 | Testing, CI/CD & Conclusion**
* **On-Screen**: Show terminal running `pytest` (all tests passing) and `.github/workflows/ci.yml`.
* **Speaker**:
  > *"Under the hood, Paper2Patent is fully containerized with Docker, covered by a 100% passing Pytest suite with zero-credential mock fallbacks, and continuously deployed via GitHub Actions.  
  > Paper2Patent proves how the Google Agent Development Kit can democratize intellectual property protection for scientists worldwide. Thank you!"*

---

## 💡 Quick Tips for Recording
1. **Resolution**: 1080p (1920x1080) at 60fps.
2. **Audio**: Crisp microphone audio with clear pronunciation.
3. **Demo Sequence**: 
   - Start with `streamlit run src/ui/app.py`
   - Show the 4 tabs quickly
   - Switch to terminal to show `pytest -v tests/` and `docker compose up`
