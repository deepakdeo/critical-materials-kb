"""Streamlit chatbot UI for the Critical Materials Knowledge Base."""

import streamlit as st

# Must be first Streamlit call
st.set_page_config(
    page_title="Critical Materials KB",
    page_icon="🔬",
    layout="wide",
)

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.generation.chains import query  # noqa: E402


def init_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_sidebar() -> dict:
    """Render the sidebar with filter options."""
    st.sidebar.title("Filters")

    materials_input = st.sidebar.text_input(
        "Materials (comma-separated)",
        placeholder="tungsten, nickel, cobalt",
    )
    materials = (
        [m.strip() for m in materials_input.split(",") if m.strip()]
        if materials_input
        else None
    )

    doc_type = st.sidebar.selectbox(
        "Document Type",
        options=[
            "All",
            "usgs_mcs",
            "gao_report",
            "crs_report",
            "doe_report",
            "dpa_announcement",
            "industry",
            "regulatory",
            "custom_analysis",
        ],
    )
    doc_types = [doc_type] if doc_type != "All" else None

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Critical Materials Knowledge Base**\n\n"
        "Ask questions about U.S. critical materials "
        "supply chains. Every answer is cited and verified."
    )

    return {"materials": materials, "doc_types": doc_types}


def render_response(response) -> None:
    """Render a query response with answer, sources, and metadata."""
    # Answer
    st.markdown(response.answer)

    # Verification badge
    verdict = response.verification.verdict
    severity = response.verification.severity
    if verdict == "PASS":
        st.success(f"Verified: {verdict}")
    elif severity == "minor":
        st.warning(f"Verified: {verdict} (minor issues)")
    else:
        st.error(f"Verified: {verdict} ({severity})")

    if response.verification.issues:
        with st.expander("Verification Details"):
            for issue in response.verification.issues:
                st.markdown(f"- {issue}")

    # Sources
    if response.sources:
        with st.expander(f"Sources ({len(response.sources)})"):
            for i, src in enumerate(response.sources, 1):
                st.markdown(
                    f"**{i}.** {src.name} {src.page} — {src.section}"
                )

    # Metadata
    with st.expander("Query Metadata"):
        meta = response.metadata
        cols = st.columns(4)
        cols[0].metric("Query Type", meta.get("query_type", "N/A"))
        cols[1].metric("Chunks Retrieved", meta.get("chunks_retrieved", 0))
        cols[2].metric("After Rerank", meta.get("chunks_after_rerank", 0))
        cols[3].metric("Latency", f"{meta.get('latency_ms', 0)}ms")


def main() -> None:
    """Main Streamlit application."""
    st.title("Critical Materials Knowledge Base")
    st.caption(
        "Hybrid RAG chatbot for U.S. critical materials supply chain intelligence"
    )

    init_session_state()
    filters = render_sidebar()

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "response" in message:
                render_response(message["response"])
            else:
                st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask a supply chain question..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching and analyzing..."):
                response = query(
                    question=prompt,
                    materials=filters.get("materials"),
                    doc_types=filters.get("doc_types"),
                )
                render_response(response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response.answer,
            "response": response,
        })


if __name__ == "__main__":
    main()
