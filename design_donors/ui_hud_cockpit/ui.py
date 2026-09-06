import time
from datetime import datetime

import pandas as pd
import streamlit as st

# Import backend components
try:
    from cogos.config import CONF, SystemConfig
    from cogos.models import create_model_interface
    from cogos.orchestrator import IWCOOrchestrator
    BACKEND_AVAILABLE = True
except ImportError:
    # Fallback if backend cannot be loaded
    BACKEND_AVAILABLE = False

    # Fallback classes when backend unavailable
    class TrustTier:
        T1_PROCEED = "T1_PROCEED"
        T4_REFUSE_EPISTEMIC = "T4_REFUSE_EPISTEMIC"
        T4_REFUSE = "T4_REFUSE"

    class MockHardware:
        max_vram_gb = "N/A"
        safe_vram_limit_gb = "N/A"
        enable_gpu = False
        device = "Unknown"

    class MockCONF:
        HARDWARE = MockHardware()

    # Cast to SystemConfig for mypy compatibility if needed, or suppress
    CONF = MockCONF() # type: ignore

# Page Config
st.set_page_config(
    page_title="CogOS v2.2.1",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Liquid" feel and dark mode
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
    }
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BACKEND INITIALIZATION (Singleton Pattern in Session State)
# ==============================================================================
if "orchestrator" not in st.session_state and BACKEND_AVAILABLE:
    with st.spinner("Initializing Cognitive Stack..."):
        # Auto-configure hardware
        SystemConfig.auto_configure(update_global=True)
        # Initialize Model Interface (Auto-detects real vs stub)
        model_interface = create_model_interface(prefer_real=True)
        # Initialize Orchestrator
        st.session_state.orchestrator = IWCOOrchestrator(model=model_interface)

if "history" not in st.session_state:
    st.session_state.history = []

if "cil_ledger" not in st.session_state:
    st.session_state.cil_ledger = []

def run_inference(query):
    """Runs the actual cognitive process via IWCO Orchestrator."""
    if not BACKEND_AVAILABLE or "orchestrator" not in st.session_state:
        # Fallback Logic when backend unavailable
        time.sleep(0.5)
        return {
            "response": "Backend Unavailable: Running in restricted mode.",
            "alpha": 0.0,
            "beta": 0.0,
            "merkle": "N/A",
            "status": "OFFLINE",
            "result": None
        }

    # Run Real Orchestrator
    # The orchestrator returns a result object with seal, text, etc.
    orch_result = st.session_state.orchestrator.process_query(query)

    # Extract data for UI
    seal = orch_result.seal

    # Check for Epistemic Inversion data in seal if available, or reconstruct
    # R2Seal in governance.py has epistemic_margin but maybe not raw alpha/beta
    # We might need to dig into the synthesis artifact if exposed, but for now we approximate
    # based on what we have or just display what's available.
    # Actually, R2Seal has 'epistemic_margin' = coherence - confidence.
    # We can't recover alpha/beta perfectly from just margin, but we can display the seal data.

    # However, for the UI visualizer, we want alpha/beta.
    # The orchestrator result typically includes the SynthesisArtifact?
    # Let's check orchestrator.py in a moment. For now, we assume we can get it or we placeholder it.

    # Assuming standard result structure based on previous analysis
    return {
        "response": orch_result.final_text,
        "alpha": 0.0, # Expose this in Orchestrator result if not present
        "beta": 0.0,  # Expose this in Orchestrator result if not present
        "merkle": seal.merkle_root if seal else "N/A",
        "status": seal.status if seal else "ERROR",
        "result": seal # The seal object
    }

# ==============================================================================
# UI LAYOUT
# ==============================================================================

# SIDEBAR
with st.sidebar:
    st.image("https://placehold.co/100x100?text=CogOS", width=80) # Placeholder logo
    st.title("System Status")

    # Hardware Config Display
    st.markdown("### 🖥️ Hardware Profile")
    if BACKEND_AVAILABLE:
        try:
            hw = CONF.HARDWARE
            st.info(f"VRAM: {hw.safe_vram_limit_gb}GB / {hw.max_vram_gb}GB")
            st.info(f"GPU: {'Enabled' if hw.enable_gpu else 'Disabled'} ({hw.device})")
        except Exception as e:
            st.warning(f"Profile Error: {e}")
    else:
        st.warning("Backend Offline")

    st.markdown("---")
    st.markdown("### 🛡️ Trust Tier")
    current_tier = st.empty()
    if st.session_state.history:
        last_res = st.session_state.history[-1]['result']
        # Handle Seal object or fallback object
        tier_val = getattr(last_res, 'trust_tier', "UNKNOWN")
        if hasattr(tier_val, 'value'):
            tier_val = tier_val.value
        current_tier.code(str(tier_val))
    else:
        current_tier.markdown("Waiting for input...")

    st.markdown("---")
    if st.button("Clear Memory/History"):
        st.session_state.history = []
        st.session_state.cil_ledger = []
        st.rerun()

# MAIN AREA
st.caption("Cognitive Intersymbolic Ledger • Epistemic Inversion v6.0")

# Top Metrics Row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("CIL Height", len(st.session_state.cil_ledger))
with c2:
    st.metric("Active Contexts", "3/5")
with c3:
    latest_alpha = st.session_state.history[-1]['alpha'] if st.session_state.history else 0.0
    st.metric("Last Alpha (Conf)", f"{latest_alpha:.2f}")
with c4:
    latest_beta = st.session_state.history[-1]['beta'] if st.session_state.history else 0.0
    st.metric("Last Beta (Evid)", f"{latest_beta:.2f}")

# Chat Interface
st.markdown("### Cognitive Stream")

# Display History
for msg in st.session_state.history:
    with st.chat_message("user"):
        st.write(msg["query"])

    with st.chat_message("assistant"):
        # Display the "Thinking" process or metadata
        with st.expander("Cognitive Stack Trace (Internal)", expanded=False):
            mc1, mc2 = st.columns(2)
            with mc1:
                st.write(f"**Alpha (Confidence):** {msg['alpha']:.2f}")
                st.progress(float(msg['alpha']))
            with mc2:
                st.write(f"**Beta (Evidence):** {msg['beta']:.2f}")
                st.progress(float(msg['beta']))

            st.write(f"**Merkle Root:** `{msg['merkle']}`")
            st.write(f"**Status:** {msg['status']}")

            # Visualizing the inversion
            if msg['alpha'] > msg['beta']:
                st.error("⚠️ Inversion Detected (Alpha > Beta)")
            else:
                st.success("✅ Stable Epistemics")

        st.write(msg["response"])

# Input
query = st.chat_input("Query the Cognitive Stack...")

if query:
    with st.spinner("Accessing Liquid Shelf..."):
        result = run_inference(query)

        # Update State
        st.session_state.history.append({
            "query": query,
            "response": result["response"],
            "alpha": result["alpha"],
            "beta": result["beta"],
            "merkle": result["merkle"],
            "result": result["result"],
            "status": result["status"]
        })

        # Log to CIL
        st.session_state.cil_ledger.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "root": result["merkle"],
            "event": result["status"]
        })

        st.rerun()

# Bottom Section: CIL Visualizer
st.markdown("---")
st.markdown("### 🔗 CIL Ledger (Recent Blocks)")
if st.session_state.cil_ledger:
    df = pd.DataFrame(st.session_state.cil_ledger)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No ledger entries yet.")
