"""
Standalone one-page showcase for the credit-union member chatbot.

Fully decoupled from the real app (no Flask, no MongoDB, no React) -- renders a fixed demo
member (the same DEMO0001 member used in the local widget demo) as a replica of the real
PMG360 member-profile page, plus the chatbot. This reuses the REAL stylesheet
(src/style/Iframe.css, copied verbatim into assets/) and the real widget class names
(.widget, .banner, .slider, .bullet, .circle-member-segment, ...) instead of hand-rolled CSS,
so it stays visually in sync with the actual product's styling.

Run:
    streamlit run app.py
"""

import base64
import datetime
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

ASSETS_DIR = Path(__file__).parent / "assets"


def _b64(filename: str) -> str:
    return base64.b64encode((ASSETS_DIR / filename).read_bytes()).decode()


LOGO_B64 = _b64("pmg_logo.png")
FOOTER_LOGO_B64 = _b64("pmg_logo_footer.png")
RET_SCORE_ICON_B64 = _b64("ret-score.png")
TRAJECTORY_ICON_B64 = {
    "upward": _b64("trajectory_upward.png"),
    "downward": _b64("trajectory_downward.png"),
    "straight": _b64("trajectory_straight.png"),
}

# The real stylesheet, copied verbatim from the frontend (src/style/Iframe.css) -- reused as-is
# rather than re-derived, so widget styling stays in sync with the actual product.
REAL_IFRAME_CSS = (ASSETS_DIR / "Iframe.css").read_text()

PAGE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;500;600;700&family=Public+Sans:wght@400;500;600;700&family=Poppins:wght@500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Open Sans', sans-serif;
}}
.block-container {{ max-width: 1020px; }}

.pmg-header {{
    display: flex;
    align-items: center;
    gap: 16px;
    background: #042231;
    padding: 16px 24px;
    border-radius: 8px;
    margin-bottom: 24px;
}}
.pmg-header img {{ height: 36px; }}
.pmg-header .pmg-title {{ color: white; font-family: 'Public Sans', sans-serif; font-size: 1.1rem; font-weight: 600; }}
.pmg-header .pmg-subtitle {{ color: #ABCAED; font-size: 0.85rem; }}

div.stButton > button {{ background-color: #3A82D4; color: white; border: none; font-weight: 600; }}
div.stButton > button:hover {{ background-color: #2C75C9; color: white; }}
[data-testid="stChatMessage"] {{ background-color: #EEF4FB; border-radius: 8px; }}

{REAL_IFRAME_CSS}

/* Additions for pieces this demo needs that the real per-widget CSS doesn't cover on its own
   (the header circle/banner layout and gauge axis rows are built inline in the real JSX with
   Tailwind utility classes we don't have here -- these replicate that layout only). */
.pmg-header-row {{ display: flex; align-items: stretch; }}
.pmg-segment-circle {{
    flex-shrink: 0;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: linear-gradient(to right, #CBD366, #3F85D6);
    padding: 5px;
    z-index: 2;
}}
.pmg-segment-circle-inner {{
    width: 100%; height: 100%; border-radius: 50%; background: white;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
}}
.pmg-gauge-axis-row {{ display: flex; align-items: center; }}
.pmg-gauge-axis-row .axis-label {{ width: 34px; flex-shrink: 0; text-align: center; }}
.pmg-gauge-captions {{ display: flex; justify-content: space-between; padding: 0 34px; font-size: 0.85rem; }}
</style>
"""

# ----------------------------------------------------------------------------
# Glossary -- same definitions/playbook logic as the real chatbot_service.py,
# duplicated here on purpose so this demo has zero dependency on the main app.
# ----------------------------------------------------------------------------
FIELD_GLOSSARY: dict[str, str] = {
    "age": "Member age at the reference month.",
    "tenure": "Member tenure in years.",
    "trajectory_segment": (
        "One of: straight, upward, or downward. Upward = promising, engage proactively. "
        "Downward = worth a supportive conversation soon, opportunity to help them course-correct."
    ),
    "member_segment": (
        "One of 15 values: EM1, EM2, D1, D3, D2, E1, E3, E2, T1, T3, T2, M1, M2, R1, R2.\n"
        "Every member belongs to a life stage (EM, D, E, T, M, R) and within that stage, a "
        "financial potential tier -- tier 1 highest, tier 3 medium, tier 2 lowest."
    ),
    "wallet_share": (
        "Percentage of the member's total liquid wealth (inside and outside the credit union) "
        "held at the credit union. Low wallet share on a financially strong member is one of the "
        "most valuable signals: real money sitting elsewhere that could be brought in-house."
    ),
    "retention_score": (
        "-50 to +50. Higher = more loyal/likely to stay, lower = more at risk of leaving.\n"
        "- Below -25: nearly gone. -25 to 0: cooling off, reachable. 0 to +25: stable, highest "
        "growth opportunity. Above +25: loyal and deeply engaged."
    ),
    "engagement_score": (
        "0-100 index from product breadth, transaction depth, digital adoption, relationship "
        "enablers, and balance stickiness. 0 = very disengaged, 100 = very engaged."
    ),
    "clv_percent_for_segment": (
        "Where this member's predicted 5-year lifetime value ranks against other members in the "
        "same segment, as a percentile (0-100)."
    ),
    "wealth_opportunity_score": (
        "0-100: how good a potential customer someone is. 0-25: not a priority. 76-100: ready to "
        "go, prioritize."
    ),
    "next_best_product_recommendations": "Recommended next product(s), based on similar members -- don't invent new ones.",
    "advices": "Conversation prompts for the member's life stage, in priority order.",
    "engagement_opportunities": "A short list of practical next steps for the advisor.",
    "product_summary": "Which accounts/products the member currently holds with the credit union.",
}

# ----------------------------------------------------------------------------
# Fixed demo member -- the same DEMO0001 member shown in the local widget demo.
# ----------------------------------------------------------------------------
MEMBER_SEGMENT = "T1"
MEMBER_SEGMENT_TITLE = "Transitioning 1: Engagers"
TENURE_YEARS = 8
TRAJECTORY = "upward"
TRAJECTORY_TREND = "M1: Engagers"

PRODUCTS_HELD = [("Chequing account", True), ("Savings account", True), ("Investments", False), ("Loans", True)]
ACCOUNTS_COUNT = sum(1 for _, has in PRODUCTS_HELD if has)
SIMILAR_MEMBERS_HAVE = ["Investments", "Credit card"]
TOP_ENGAGEMENT_OPPORTUNITIES = [
    "Ensure current chequing account(s) is/are meeting client needs",
    "Ensure current savings account(s) is/are meeting client needs",
    "Discuss developing a financial plan and schedule a follow-up",
]
ADVICE_FACTORS = [
    "Advice on buying first home",
    "Integrating life insurance as part of your financial plan",
    "Setting a target savings rate to ensure you have enough savings to fund your retirement",
    "The benefits of deferring taxes with registered accounts (e.g. RRSPs)",
    "Following a budget",
]
INDUSTRY_ENGAGEMENT = [
    ("Perceived value of advice", 0.9, 0.75),
    ("Trust in financial industry", 0.7, 0.6),
    ("Trust in financial professionals", 0.7, 0.6),
]
INSIGHTS = {
    "Advice considerations": (
        "T1 members respond well to concrete, near-term milestones (first home, RRSP deadlines) "
        "rather than abstract long-term planning."
    ),
    "Connecting with T1s": (
        "Lead with a life-stage check-in before products -- this segment values being asked about "
        "their situation before being sold to."
    ),
    "Considerations for financial providers & professionals": (
        "Above-average trust in advice means a single well-timed conversation can shift multiple "
        "products at once -- don't split this into several small asks."
    ),
}
WALLET_SHARE = 22.5
WALLET_SHARE_SEGMENT_AVERAGE = 22.5

MEMBER = {
    "member_segment": MEMBER_SEGMENT,
    "tenure": TENURE_YEARS,
    "trajectory_segment": TRAJECTORY,
    "retention_score": 12.5,
    "engagement_score": 61,
    "clv_percent_for_segment": 62,
    "wallet_share": WALLET_SHARE,
    "wealth_opportunity_score": 70,
    "advices": ", ".join(ADVICE_FACTORS),
    "engagement_opportunities": ", ".join(TOP_ENGAGEMENT_OPPORTUNITIES),
    "next_best_product_recommendations": ", ".join(SIMILAR_MEMBERS_HAVE),
    "product_summary": ", ".join(label for label, has in PRODUCTS_HELD if has) + " (no investments)",
}

MODEL_OPTIONS = {
    "Claude Sonnet 5 (Anthropic)": ("anthropic", "claude-sonnet-5"),
    "Claude Opus 4.8 (Anthropic)": ("anthropic", "claude-opus-4-8"),
    "Llama 3.2 1B (local Ollama)": ("ollama", "llama3.2:1b"),
}

# Anthropic per-MTok pricing (intro pricing through 2026-08-31 for Sonnet 5; bump these after
# that date -- see Anthropic's pricing page). Ollama models are local/free, so they're just absent.
INPUT_COST_PER_MTOK = {"claude-sonnet-5": 2.00, "claude-opus-4-8": 5.00}
OUTPUT_COST_PER_MTOK = {"claude-sonnet-5": 10.00, "claude-opus-4-8": 25.00}

SYSTEM_PROMPT_TEMPLATE = """You are an assistant helping a credit union financial advisor understand one \
member's profile so they can have a better conversation with that member.

Rules:
- Ground every answer in the record and glossary below. Don't invent numbers, products, or facts not \
present in them.
- You may explain and combine what's already in "advices" and "next_best_product_recommendations", but \
don't invent new product recommendations beyond what's listed.
- Keep answers short and conversational.
- If asked something the record/glossary doesn't cover, say so plainly instead of guessing.

Glossary:
{glossary}

Member record:
{member_record}
"""


def build_system_prompt(member_row: dict) -> str:
    glossary_text = "\n\n".join(f"{field}: {definition}" for field, definition in FIELD_GLOSSARY.items())
    record_text = "\n".join(f"{field}: {value}" for field, value in member_row.items() if str(value).strip())
    return SYSTEM_PROMPT_TEMPLATE.format(glossary=glossary_text, member_record=record_text)


def stream_reply(member_row: dict, history: list[dict], message: str, provider: str, model_name: str, metrics: dict):
    """Streams the reply word-by-word (same UX as the real widget) and, once exhausted, fills
    `metrics` with `response_time_ms` (time to first word, not total generation time -- that's
    what the advisor actually experiences when the reply streams in) and `cost_usd`.
    """
    model_kwargs = {}
    if provider == "anthropic":
        # Grounded Q&A over an already-summarized member record doesn't need multi-step
        # reasoning, and adaptive thinking (on by default) adds several seconds of latency here.
        model_kwargs["thinking"] = {"type": "disabled"}
        model_kwargs["effort"] = "low"

    chat_model = init_chat_model(model_name, model_provider=provider, **model_kwargs)
    messages = [{"role": "system", "content": build_system_prompt(member_row)}]
    messages += [{"role": turn["role"], "content": turn["content"]} for turn in history]
    messages.append({"role": "user", "content": message})

    start_time = time.perf_counter()
    input_tokens = output_tokens = 0
    time_to_first_token_ms = None
    for chunk in chat_model.stream(messages):
        text = (
            chunk.content
            if isinstance(chunk.content, str)
            else "".join(b.get("text", "") for b in chunk.content if isinstance(b, dict) and b.get("type") == "text")
        )
        if text:
            if time_to_first_token_ms is None:
                time_to_first_token_ms = round((time.perf_counter() - start_time) * 1000)
            yield text
        if chunk.usage_metadata:
            input_tokens = chunk.usage_metadata.get("input_tokens") or input_tokens
            output_tokens = chunk.usage_metadata.get("output_tokens") or output_tokens

    cost_usd = (
        input_tokens / 1_000_000 * INPUT_COST_PER_MTOK.get(model_name, 0)
        + output_tokens / 1_000_000 * OUTPUT_COST_PER_MTOK.get(model_name, 0)
    )
    metrics["response_time_ms"] = (
        time_to_first_token_ms
        if time_to_first_token_ms is not None
        else round((time.perf_counter() - start_time) * 1000)
    )
    metrics["cost_usd"] = round(cost_usd, 6)


# ----------------------------------------------------------------------------
# Widget replica -- transcribes the real JSX (Header.js, Retention.js,
# ProductSummaryAndOpportunities/*, IndustryEngagement.js, WalletShare.js, Trajectory.js,
# Advice.js, Insights.js) to static HTML using the REAL class names, so REAL_IFRAME_CSS styles
# it without any hand-rolled CSS of our own.
# ----------------------------------------------------------------------------


def _flatten(html: str) -> str:
    """Collapses a pretty-printed HTML template to one line.

    Streamlit's markdown renderer treats 4+ leading spaces after a blank line as a code block
    (standard Markdown behavior) -- an indented multi-line HTML f-string trips that rule partway
    through and the rest renders as literal escaped tags instead of markup.
    """
    return "".join(line.strip() for line in html.splitlines())


def render_html(html: str) -> None:
    st.markdown(_flatten(html), unsafe_allow_html=True)


def _gauge_color(value: float, low: float, high: float) -> str:
    if value < low:
        return "#EE2923"
    if value > high:
        return "#30B449"
    return "#ffb400"


def _gauge_block(heading_html: str, value: float, low: float, high: float, percent: float, left_label: str, right_label: str, left_caption: str, right_caption: str) -> str:
    color = _gauge_color(value, low, high)
    percent = max(0, min(100, percent))
    return f"""
    <h6 class="subtitle iframe-heading py-1 mb-0">{heading_html}</h6>
    <div class="graphic">
        <div class="middle bold"><span><big style="color:{color}; font-weight:bold;">{value:g}</big></span></div>
        <div class="pmg-gauge-axis-row">
            <span class="axis-label">{left_label}</span>
            <div class="slider"><div class="bullet" style="left:{percent}%"></div></div>
            <span class="axis-label">{right_label}</span>
        </div>
        <div class="pmg-gauge-captions"><small>{left_caption}</small><small>{right_caption}</small></div>
    </div>
    """


def render_header() -> None:
    trajectory_b64 = TRAJECTORY_ICON_B64.get(MEMBER["trajectory_segment"])
    render_html(f"""
    <div class="iframe"><div class="widget header">
        <div class="pmg-header-row">
            <div class="pmg-segment-circle"><div class="pmg-segment-circle-inner">
                <h6 class="circle-member-segment">{MEMBER_SEGMENT}</h6>
                <img src="data:image/png;base64,{trajectory_b64}" width="26" alt="trajectory" />
            </div></div>
            <div class="banner master">
                <div class="relative left-5 self-center">
                    <h6 class="font-bold iframe-heading"><strong>{MEMBER_SEGMENT_TITLE}</strong> <span class="info-button">&#9432;</span></h6>
                    <h6 class="font-bold iframe-heading">Member for {TENURE_YEARS} year(s) <span class="info-button">&#9432;</span></h6>
                </div>
                <div class="banner-button-container"><span style="font-size:1.3rem;">&#128202; &#128438;</span></div>
            </div>
        </div>
    </div></div>
    """)
    today = datetime.date.today().isoformat()
    render_html(f'<div class="timestamp">Last update: {today}</div>')


def render_retention_card() -> None:
    retention_icon = f'<img class="w-10 h-10 mr-1" src="data:image/png;base64,{RET_SCORE_ICON_B64}" alt="retention score" style="width:32px; display:inline-block; vertical-align:middle;" />'
    heading1 = f'{retention_icon}Retention Score <span class="info-button">&#9432;</span> <span class="feedback">&#128077;&#128078;</span>'
    gauge1 = _gauge_block(heading1, MEMBER["retention_score"], -20, 20, MEMBER["retention_score"] + 50, "-50", "+50", "Likely at risk", "Very low risk")

    heading2 = 'Engagement Score <span class="info-button">&#9432;</span>'
    gauge2 = _gauge_block(heading2, MEMBER["engagement_score"], -25, 25, MEMBER["engagement_score"] + 50, "-50", "+50", "Disengaged", "Engaged")

    heading3 = 'Member Lifetime Value <span class="info-button">&#9432;</span>'
    gauge3 = _gauge_block(heading3, MEMBER["clv_percent_for_segment"], 25, 75, MEMBER["clv_percent_for_segment"], "0%", "100%", "Low", "High")

    render_html(f"""
    <div class="iframe"><div class="widget"><div class="flex flex-col text-center p-[10px]">
        {gauge1}{gauge2}{gauge3}
    </div></div></div>
    """)


def render_product_summary_card() -> None:
    rows_html = f'<div class="product-row"><span class="font-bold">Accounts</span><span class="ml-auto font-bold">{ACCOUNTS_COUNT}</span></div>'
    for label, has in PRODUCTS_HELD:
        mark = '<span style="color:#15803d; font-weight:bold;">&#10003;</span>' if has else '<span style="color:#dc2626; font-weight:bold;">&#10007;</span>'
        rows_html += f'<div class="product-row"><span>{label}</span><span class="ml-auto">{mark}</span></div>'

    similar_html = "".join(f"<li>{item}</li>" for item in SIMILAR_MEMBERS_HAVE)
    opportunities_html = "".join(f"<li>{item}</li>" for item in TOP_ENGAGEMENT_OPPORTUNITIES)

    render_html(f"""
    <div class="iframe"><div class="widget"><div class="inner text-center">
        <h6 class="subtitle iframe-heading">Product Summary and Opportunities</h6>
        <div style="display:flex; gap:24px; justify-content:center; text-align:left;">
            <div style="flex:2; min-width:170px;">
                <h6 class="text-left-override w-full">Member Has <span class="info-button">&#9432;</span></h6>
                {rows_html}
            </div>
            <div style="flex:3; min-width:210px;">
                <h6 class="text-left-override w-full">Similar Members Have <span class="info-button">&#9432;</span></h6>
                <ul class="product-summary-and-opportunities-list">{similar_html}</ul>
                <h6 class="text-left-override w-full">Top Engagement Opportunities <span class="info-button">&#9432;</span></h6>
                <ul class="product-summary-and-opportunities-list">{opportunities_html}</ul>
            </div>
        </div>
    </div></div></div>
    """)


def render_industry_engagement_card() -> None:
    rows_html = ""
    for description, value, average in INDUSTRY_ENGAGEMENT:
        label = "Above average" if value > average else ("Below average" if value < average else "Average")
        dots = ""
        for i in range(5):
            fill_amount = max(0, min(100, (value - 0.2 * i) * 500))
            dots += f'<div class="bullet"><div class="fill" style="width:{fill_amount}%"></div></div>'
        rows_html += f"""
        <div class="row">
            <div class="col-7"><span class="iframe-heading">{description}</span></div>
            <div class="col-5 pb-2 text-center">{dots}<small>{label}</small></div>
        </div>
        """
    render_html(f"""
    <div class="iframe"><div class="widget"><div class="inner member-segment {MEMBER_SEGMENT}">
        <div class="text-center"><h6 class="subtitle iframe-heading">Industry Engagement <span class="info-button">&#9432;</span></h6></div>
        {rows_html}
    </div></div></div>
    """)


def render_wallet_share_card() -> None:
    render_html(f"""
    <div class="iframe"><div class="widget"><div class="inner text-center">
        <h6 class="subtitle iframe-heading">Estimated Share of Wallet <span class="info-button">&#9432;</span></h6>
        <h3 class="iframe-heading"><strong>{WALLET_SHARE:g}%</strong></h3>
        <p class="iframe-heading">Investable Assets</p>
        <p class="iframe-heading">Average {MEMBER_SEGMENT} has {WALLET_SHARE_SEGMENT_AVERAGE:g}% with us</p>
    </div></div></div>
    """)


def render_trajectory_card() -> None:
    trajectory_b64 = TRAJECTORY_ICON_B64.get(MEMBER["trajectory_segment"])
    render_html(f"""
    <div class="iframe"><div class="widget"><div class="inner text-center">
        <h6 class="subtitle iframe-heading margin-override">Trajectory <span class="info-button">&#9432;</span></h6>
        <img class="mx-auto" src="data:image/png;base64,{trajectory_b64}" alt="trajectory arrow" style="width:50px;" />
        <div>Most likely to transition to <strong>{TRAJECTORY_TREND}</strong></div>
    </div></div></div>
    """)


def render_advice_card() -> None:
    items_html = "".join(f"<li>{item} &#128279;</li>" for item in ADVICE_FACTORS)
    render_html(f"""
    <div class="iframe"><div class="widget" style="padding:10px;">
        <h6 class="subtitle iframe-heading">Advice Factors <span class="info-button">&#9432;</span><br/><small>Key contributors to financial success</small></h6>
        <ul>{items_html}</ul>
    </div></div>
    """)


def render_insights() -> None:
    with st.expander(f"Insights into connecting with a {MEMBER_SEGMENT} &nbsp;&nbsp; View insights"):
        for key, text in INSIGHTS.items():
            st.markdown(f"**{key}**")
            st.write(text)


def render_footer() -> None:
    render_html(f"""
    <div style="display:flex; align-items:center; justify-content:flex-end; gap:8px; margin-top:8px; color:#042231;">
        Powered by <img src="data:image/png;base64,{FOOTER_LOGO_B64}" width="100" alt="PMG Intelligence" />
    </div>
    """)


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
st.set_page_config(page_title="PMG360 Member Chatbot Demo", page_icon=str(ASSETS_DIR / "favicon.png"), layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="pmg-header">
        <img src="data:image/png;base64,{LOGO_B64}" alt="PMG logo" />
        <div>
            <div class="pmg-title">PMG360 Member Chatbot</div>
            <div class="pmg-subtitle">Showcase -- a replica of the real member profile widget</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

provider, model_name = MODEL_OPTIONS["Claude Sonnet 5 (Anthropic)"]

render_header()

col1, col2 = st.columns([5, 7])
with col1:
    render_retention_card()
with col2:
    render_product_summary_card()

col3, col4, col5 = st.columns([6, 3, 3])
with col3:
    render_industry_engagement_card()
with col4:
    render_wallet_share_card()
with col5:
    render_trajectory_card()

col6, _ = st.columns([6, 6])
with col6:
    render_advice_card()

render_insights()
render_footer()

st.divider()
st.markdown('<h6 class="subtitle iframe-heading py-0 mb-0" style="text-align:center;">Ask AI</h6>', unsafe_allow_html=True)

for turn in st.session_state.chat_history:
    with st.chat_message(turn["role"]):
        st.write(turn["content"])
        if turn["role"] == "assistant" and turn.get("response_time_ms") is not None:
            st.caption(f"first word in {turn['response_time_ms'] / 1000:.1f}s · ${turn['cost_usd']:.4f}")

if not st.session_state.chat_history:
    st.caption('Ask a question about this member -- e.g. "why is their retention score low?"')

question = st.chat_input("Ask about this member...")
if question:
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    metrics = {}
    with st.chat_message("assistant"):
        try:
            reply = st.write_stream(
                stream_reply(MEMBER, st.session_state.chat_history[:-1], question, provider, model_name, metrics)
            )
        except Exception as error:  # noqa: BLE001 -- surface any provider/config error directly in the demo UI
            reply = f"Error calling the model: {error}"
            metrics = {}
        if metrics:
            st.caption(f"first word in {metrics['response_time_ms'] / 1000:.1f}s · ${metrics['cost_usd']:.4f}")
    st.session_state.chat_history.append({"role": "assistant", "content": reply, **metrics})
