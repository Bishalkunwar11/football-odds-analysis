"""Streamlit dashboard for the football odds analysis system."""

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so that ``src`` is importable
# when Streamlit rewrites sys.path[0] to the script's directory.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import plotly.express as px
import streamlit as st

from src.api_client import OddsAPIClient
from src.analyzer import OddsAnalyzer
from src.bet_calculator import BetCalculator
from src.config import LEAGUES, SHARP_BOOKMAKERS
from src.db_manager import DBManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ApexOdds Pro | Value Bets Terminal",
    page_icon="\u26bd",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Premium Sportsbook UI – DraftKings / Bet365 / FanDuel inspired dark theme
# ---------------------------------------------------------------------------
DARK_THEME = {
    "paper_bgcolor": "#0D1B2A",
    "plot_bgcolor": "#0D1B2A",
    "font_color": "#E8EAED",
    "gridcolor": "rgba(0,200,83,0.08)",
    "colorway": ["#00C853", "#FFD700", "#00E676", "#40C4FF", "#FF6B35", "#E040FB"],
}

# Load Google Fonts via <link> tags so they are not blocked by CSP or
# sandbox restrictions that prevent @import inside <style> blocks.
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:'
    'wght@400;500;600;700;800;900&family=JetBrains+Mono:'
    'wght@500;700&display=swap" rel="stylesheet">'
    '<link href="https://fonts.googleapis.com/css2?family=Material+'
    'Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"'
    ' rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    /* ── Global reset ── */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    /* ── Material Symbols ── */
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined';
        font-weight: normal;
        font-style: normal;
        font-size: 24px;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-rendering: optimizeLegibility;
        font-feature-settings: 'liga';
    }

    /* ── Full-screen background image ── */
    .stApp {
        background: url('https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=1920&q=80') no-repeat center center fixed;
        background-size: cover;
    }
    .stApp::before {
        content: '';
        position: fixed;
        inset: 0;
        background: rgba(5,10,20,0.88);
        pointer-events: none;
        z-index: 0;
    }
    .main, [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {
        background: transparent !important;
    }
    header[data-testid="stHeader"] {
        background: rgba(5,10,20,0.7) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
    }
    .main .block-container {
        padding-top: 1rem;
    }

    /* ── Custom scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(13,27,42,0.5); }
    ::-webkit-scrollbar-thumb { background: rgba(26,35,50,0.8); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #00C853; }

    /* ── Navigation panel ── */
    .nav-panel {
        background: rgba(20, 23, 32, 0.85);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 0.8rem;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }
    .nav-item {
        display: block;
        width: 100%;
        padding: 0.7rem 1rem;
        margin-bottom: 0.3rem;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.06);
        background: rgba(13,27,42,0.4);
        color: #8899AA;
        font-weight: 600;
        font-size: 0.82rem;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: left;
    }
    .nav-item:hover {
        background: rgba(0,200,83,0.1);
        color: #E8EAED;
        border-color: rgba(0,200,83,0.15);
    }
    .nav-item.active {
        background: linear-gradient(135deg, #00C853 0%, #00E676 100%);
        color: #0D1B2A;
        font-weight: 700;
        border-color: transparent;
        box-shadow: 0 0 20px rgba(0,200,83,0.4);
    }

    /* ── Native metric cards – glassmorphism ── */
    div[data-testid="stMetric"] {
        background: rgba(13,27,42,0.55) !important;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1rem 1.25rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: #8899AA !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #00C853, #00E676, #40C4FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #00E676 !important;
    }

    /* ── Buttons – green gradient with glow ── */
    div.stButton > button {
        background: linear-gradient(135deg, #00C853 0%, #00E676 100%) !important;
        color: #0D1B2A !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        padding: 0.55rem 1.5rem !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 2px 12px rgba(0,200,83,0.3) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 24px rgba(0,200,83,0.5) !important;
        background: linear-gradient(135deg, #00E676 0%, #69F0AE 100%) !important;
    }
    div.stButton > button:active {
        transform: translateY(0px) !important;
    }

    /* ── Sidebar – glassmorphism branded panel ── */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(0,200,83,0.15) !important;
    }
    section[data-testid="stSidebar"] > div {
        background: rgba(20, 23, 32, 0.9) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
    }
    section[data-testid="stSidebar"] .stSelectbox,
    section[data-testid="stSidebar"] .stMultiSelect {
        border-radius: 10px;
    }

    /* ── Expanders – glass effect ── */
    details[data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 12px !important;
        margin-bottom: 0.5rem !important;
        background: rgba(13,27,42,0.5) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
    }
    details[data-testid="stExpander"] summary {
        font-weight: 600 !important;
    }

    /* ── Subheader accents ── */
    .main .block-container h2 {
        border-left: 4px solid #00C853;
        padding-left: 0.75rem;
        letter-spacing: 0.02em;
        text-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }

    hr {
        border-color: rgba(0,200,83,0.12) !important;
    }

    /* ── Inputs / sliders – green accent ── */
    .stSlider [data-testid="stThumbValue"] {
        color: #00C853 !important;
    }

    /* ── Hero header – glassmorphism ── */
    .hero-header {
        background: rgba(13,27,42,0.55);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 1.8rem 2rem 1.4rem 2rem;
        margin-bottom: 1.2rem;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        box-shadow:
            0 8px 32px rgba(0,0,0,0.4),
            inset 0 1px 0 rgba(255,255,255,0.06);
    }
    .hero-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00C853, #FFD700, #00E676);
    }
    .hero-header::after {
        content: '';
        position: absolute;
        top: -50%; right: -20%;
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(0,200,83,0.08) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-header .hero-title {
        font-size: 1.65rem;
        font-weight: 800;
        color: #E8EAED;
        margin: 0;
        letter-spacing: -0.01em;
        text-shadow: 0 0 20px rgba(0,200,83,0.3), 0 2px 8px rgba(0,0,0,0.3);
    }
    .hero-header .hero-title .accent {
        color: #00C853;
        text-shadow: 0 0 30px rgba(0,200,83,0.5), 0 0 60px rgba(0,200,83,0.2);
    }
    .hero-header .hero-sub {
        font-size: 0.82rem;
        color: rgba(136,153,170,0.9);
        margin-top: 0.3rem;
        font-weight: 500;
        letter-spacing: 0.03em;
    }
    .hero-header .hero-sub .dot {
        display: inline-block;
        width: 5px; height: 5px;
        background: #00C853;
        border-radius: 50%;
        margin: 0 0.5rem;
        vertical-align: middle;
        box-shadow: 0 0 6px rgba(0,200,83,0.5);
    }

    /* ── Match cards – glassmorphism sportsbook style ── */
    .match-card {
        background: rgba(20, 23, 32, 0.85);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 0;
        margin-bottom: 0.85rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        overflow: hidden;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }
    .match-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 40px rgba(0,200,83,0.15);
        border-color: rgba(0,200,83,0.2);
    }
    .match-card .card-top {
        padding: 0.9rem 1.2rem 0.6rem 1.2rem;
    }
    .match-card .league-badge {
        display: inline-block;
        background: rgba(0,200,83,0.1);
        color: #00C853;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 0.22rem 0.6rem;
        border-radius: 20px;
        border: 1px solid rgba(0,200,83,0.2);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    .match-card .teams {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        margin-top: 0.6rem;
    }
    .match-card .team-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: #E8EAED;
        flex: 1;
        text-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }
    .match-card .team-name.away { text-align: right; }
    .match-card .vs-badge {
        font-size: 0.6rem;
        font-weight: 800;
        color: #0D1B2A;
        background: linear-gradient(135deg, #00C853, #00E676);
        padding: 0.25rem 0.55rem;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(0,200,83,0.3);
    }
    .match-card .kickoff {
        font-size: 0.7rem;
        color: #8899AA;
        margin-top: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }
    .match-card .odds-row {
        display: flex;
        gap: 0;
        border-top: 1px solid rgba(255,255,255,0.05);
        background: rgba(0,0,0,0.15);
    }
    .match-card .odds-btn {
        flex: 1;
        text-align: center;
        padding: 0.55rem 0.3rem;
        transition: background 0.2s ease, box-shadow 0.2s ease;
        cursor: pointer;
        border-right: 1px solid rgba(255,255,255,0.04);
    }
    .match-card .odds-btn:last-child { border-right: none; }
    .match-card .odds-btn:hover {
        background: rgba(0,200,83,0.18);
        box-shadow: 0 0 15px rgba(0,200,83,0.3), inset 0 0 15px rgba(0,200,83,0.1);
    }
    .match-card .odds-btn .outcome-label {
        font-size: 0.6rem;
        color: #8899AA;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
    }
    .match-card .odds-btn .odds-value {
        font-size: 1.05rem;
        font-weight: 800;
        color: #FFD700;
        margin-top: 0.1rem;
    }

    /* ── Odds movement indicators ── */
    .odds-up { color: #00E676; font-size: 0.7rem; }
    .odds-down { color: #FF6B6B; font-size: 0.7rem; }

    /* ── Stat panels – glassmorphism ── */
    .stat-panel {
        background: rgba(13,27,42,0.5);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        text-align: center;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.25);
    }
    .stat-panel .stat-label {
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #8899AA;
        margin-bottom: 0.25rem;
    }
    .stat-panel .stat-value {
        font-size: 1.35rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00C853, #00E676, #40C4FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* ── Bet slip cards – glassmorphism ── */
    .slip-card {
        background: rgba(13,27,42,0.5);
        border: 1px solid rgba(255,255,255,0.06);
        border-left: 4px solid #00C853;
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.55rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        transition: transform 0.15s ease;
    }
    .slip-card:hover {
        transform: translateX(3px);
        border-color: rgba(0,200,83,0.15);
    }
    .slip-card .slip-info { flex: 1; }
    .slip-card .slip-info .slip-match {
        font-size: 0.72rem;
        color: #8899AA;
        font-weight: 500;
    }
    .slip-card .slip-info .slip-outcome {
        font-size: 0.92rem;
        font-weight: 700;
        color: #E8EAED;
        margin-top: 0.1rem;
    }
    .slip-card .slip-odds {
        font-size: 1.15rem;
        font-weight: 800;
        color: #0D1B2A;
        background: linear-gradient(135deg, #FFD700, #FFC107);
        padding: 0.3rem 0.7rem;
        border-radius: 8px;
        margin-left: 0.75rem;
        box-shadow: 0 2px 8px rgba(255,215,0,0.3);
    }

    /* ── Value bet / Arbitrage alert cards – glassmorphism ── */
    .alert-card {
        background: rgba(13,27,42,0.5);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1.05rem 1.3rem;
        margin-bottom: 0.7rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.25);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        transition: transform 0.15s ease;
    }
    .alert-card:hover {
        transform: translateY(-2px);
        border-color: rgba(0,200,83,0.15);
    }
    .alert-card .alert-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .alert-card .alert-teams {
        font-size: 0.9rem;
        font-weight: 700;
        color: #E8EAED;
    }
    .alert-card .alert-badge {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 800;
        padding: 0.25rem 0.65rem;
        border-radius: 20px;
        letter-spacing: 0.04em;
    }
    .badge-value {
        background: rgba(0,200,83,0.12);
        color: #00E676;
        border: 1px solid rgba(0,200,83,0.3);
        animation: pulse-green 2s ease-in-out infinite;
    }
    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 0 0 rgba(0,200,83,0.3); }
        50% { box-shadow: 0 0 12px 2px rgba(0,200,83,0.25); }
    }
    .badge-arb {
        background: rgba(255,215,0,0.12);
        color: #FFD700;
        border: 1px solid rgba(255,215,0,0.3);
        animation: pulse-gold 2s ease-in-out infinite;
    }
    @keyframes pulse-gold {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255,215,0,0.3); }
        50% { box-shadow: 0 0 12px 2px rgba(255,215,0,0.25); }
    }
    .alert-card .alert-detail {
        font-size: 0.78rem;
        color: #8899AA;
        line-height: 1.6;
    }
    .alert-card .alert-detail strong {
        color: #E8EAED;
    }

    /* ── Counter badge ── */
    .count-badge {
        display: inline-block;
        background: linear-gradient(135deg, #00C853, #00E676);
        color: #0D1B2A;
        font-size: 0.8rem;
        font-weight: 800;
        padding: 0.35rem 0.95rem;
        border-radius: 20px;
        margin-bottom: 0.75rem;
        letter-spacing: 0.03em;
        box-shadow: 0 2px 10px rgba(0,200,83,0.3);
    }

    /* ── Empty state styling ── */
    .empty-state {
        text-align: center;
        padding: 2.5rem 1rem;
        color: #8899AA;
    }
    .empty-state .empty-icon {
        font-size: 2.5rem;
        margin-bottom: 0.6rem;
        opacity: 0.6;
    }
    .empty-state .empty-text {
        font-size: 0.88rem;
        font-weight: 500;
        max-width: 400px;
        margin: 0 auto;
        line-height: 1.5;
    }

    /* ── Footer – glassmorphism ── */
    .app-footer {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
        color: #556677;
        font-size: 0.72rem;
        border-top: 1px solid rgba(0,200,83,0.08);
        margin-top: 2rem;
        letter-spacing: 0.03em;
        background: rgba(13,27,42,0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 12px 12px 0 0;
    }
    .app-footer .footer-accent { color: #00C853; }

    /* ── Multiselect tags ── premium dark pills ── */
    span[data-baseweb="tag"] {
        background: linear-gradient(135deg, rgba(0,200,83,0.15), rgba(0,200,83,0.08)) !important;
        border: 1px solid rgba(0,200,83,0.3) !important;
        border-radius: 20px !important;
        color: #00E676 !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.02em !important;
    }
    span[data-baseweb="tag"] span {
        color: #00E676 !important;
    }
    span[data-baseweb="tag"] [data-testid="stMarkdownContainer"],
    span[data-baseweb="tag"] span[aria-label] {
        color: #00E676 !important;
    }
    /* Tag close/remove button */
    span[data-baseweb="tag"] span[role="presentation"] {
        color: rgba(0,200,83,0.6) !important;
    }
    span[data-baseweb="tag"] span[role="presentation"]:hover {
        color: #FF6B6B !important;
    }

    /* ── Form inputs – glassmorphism fields ── */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background-color: rgba(13,27,42,0.6) !important;
        color: #E8EAED !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 10px !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
    }
    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within,
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #00C853 !important;
        box-shadow: 0 0 12px rgba(0,200,83,0.25) !important;
    }
    /* Dropdown menus */
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"],
    ul[role="listbox"] {
        background-color: rgba(13,27,42,0.9) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 10px !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
    }
    [data-baseweb="menu"] li,
    ul[role="listbox"] li {
        color: #E8EAED !important;
    }
    [data-baseweb="menu"] li:hover,
    ul[role="listbox"] li:hover {
        background-color: rgba(0,200,83,0.12) !important;
    }

    /* ── Radio buttons ── styled chips ── */
    div[role="radiogroup"] label {
        background: rgba(13,27,42,0.5) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 20px !important;
        padding: 0.4rem 1rem !important;
        color: #8899AA !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        transition: all 0.2s ease !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
    }
    div[role="radiogroup"] label:hover {
        border-color: rgba(0,200,83,0.2) !important;
        color: #E8EAED !important;
    }
    div[role="radiogroup"] label[data-checked="true"],
    div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(135deg, #00C853 0%, #00E676 100%) !important;
        color: #0D1B2A !important;
        font-weight: 700 !important;
        border-color: transparent !important;
        box-shadow: 0 0 16px rgba(0,200,83,0.35) !important;
    }

    /* ── Slider track ── green accent ── */
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #00C853, #00E676) !important;
    }

    /* ── Responsive improvement ── */
    @media (max-width: 768px) {
        .match-card .teams {
            flex-direction: column !important;
            text-align: center !important;
        }
        .match-card .team-name.away {
            text-align: center !important;
        }
        .hero-header {
            padding: 1.2rem 1rem 1rem 1rem !important;
        }
        .hero-header .hero-title {
            font-size: 1.2rem !important;
        }
    }

    /* ── Streamlit toast/alert – glass style ── */
    .stAlert {
        background-color: rgba(13,27,42,0.7) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
    }

    /* ── Text elements ── ensure readable on glass bg ── */
    .stMarkdown, .stText, p, span, label, .stCaption {
        color: #E8EAED;
    }

    /* ── Number input spinner buttons ── */
    .stNumberInput button {
        background-color: rgba(13,27,42,0.6) !important;
        color: #00C853 !important;
        border-color: rgba(255,255,255,0.08) !important;
    }
    .stNumberInput button:hover {
        background-color: rgba(0,200,83,0.12) !important;
    }

    /* ── Plotly chart containers – glass wrapper ── */
    .stPlotlyChart {
        background: rgba(13,27,42,0.4) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 14px !important;
        padding: 0.5rem !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
    }

    /* ── Parlay Builder – DraftKings / FanDuel inspired ── */
    .parlay-summary {
        background: linear-gradient(135deg, rgba(20,23,32,0.9), rgba(26,29,38,0.95));
        border: 1px solid rgba(255,215,0,0.2);
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }
    .parlay-summary::before {
        content: '';
        display: block;
        height: 3px;
        background: linear-gradient(90deg, #FFD700, #FFC107, #FF9800);
        border-radius: 2px;
        margin-bottom: 0.9rem;
    }
    .parlay-summary .parlay-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #A0AEC0;
        margin-bottom: 0.6rem;
    }
    .parlay-summary .parlay-stats {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
    }
    .parlay-summary .parlay-stat {
        flex: 1;
        min-width: 80px;
    }
    .parlay-summary .parlay-stat .ps-label {
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8899AA;
    }
    .parlay-summary .parlay-stat .ps-value {
        font-size: 1.3rem;
        font-weight: 800;
        color: #FFD700;
        margin-top: 0.1rem;
    }
    .parlay-summary .parlay-stat .ps-value.green {
        color: #00E676;
    }

    .parlay-leg-card {
        background: rgba(20, 23, 32, 0.8);
        border: 1px solid rgba(255,255,255,0.06);
        border-left: 3px solid #FFD700;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: all 0.15s ease;
    }
    .parlay-leg-card:hover {
        border-color: rgba(255,215,0,0.25);
        background: rgba(26, 29, 38, 0.9);
    }
    .parlay-leg-card .leg-info {
        flex: 1;
    }
    .parlay-leg-card .leg-label {
        font-size: 0.88rem;
        font-weight: 700;
        color: #E8EAED;
    }
    .parlay-leg-card .leg-detail {
        font-size: 0.7rem;
        color: #8899AA;
        margin-top: 0.15rem;
    }
    .parlay-leg-card .leg-odds {
        font-size: 1rem;
        font-weight: 800;
        color: #0D1B2A;
        background: linear-gradient(135deg, #FFD700, #FFC107);
        padding: 0.25rem 0.65rem;
        border-radius: 8px;
        margin-left: 0.75rem;
        box-shadow: 0 2px 6px rgba(255,215,0,0.25);
    }
    .parlay-leg-card .leg-prob {
        font-size: 0.68rem;
        color: #A0AEC0;
        margin-left: 0.5rem;
        font-weight: 500;
    }

    .parlay-payout-box {
        background: linear-gradient(135deg, rgba(0,200,83,0.08), rgba(0,200,83,0.03));
        border: 1px solid rgba(0,200,83,0.2);
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin-top: 0.8rem;
        text-align: center;
    }
    .parlay-payout-box .payout-label {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #8899AA;
    }
    .parlay-payout-box .payout-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #00E676;
        margin-top: 0.2rem;
        text-shadow: 0 0 20px rgba(0,200,83,0.3);
    }

    /* ── Leg number badge ── */
    .leg-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        background: rgba(255,215,0,0.15);
        color: #FFD700;
        font-size: 0.7rem;
        font-weight: 800;
        border-radius: 50%;
        margin-right: 0.5rem;
        flex-shrink: 0;
    }

    /* ── Enhanced Parlay Summary v2 ── gold accent bar ── */
    .parlay-summary-v2 {
        position: relative;
        overflow: hidden;
        background: rgba(20,23,32,0.9);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.3rem 1.5rem 1.3rem 1.8rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }
    .parlay-summary-v2::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #FFD700, #FFC107);
        box-shadow: 0 0 15px rgba(251,191,36,0.3);
    }
    .parlay-summary-v2 .ps2-tag {
        font-size: 0.6rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        color: #FFD700;
        margin-bottom: 0.3rem;
    }
    .parlay-summary-v2 .ps2-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #E8EAED;
        margin-bottom: 0.9rem;
    }
    .parlay-summary-v2 .ps2-title .star {
        color: #FFD700;
    }
    .parlay-summary-v2 .ps2-stats {
        display: flex;
        gap: 2.5rem;
        flex-wrap: wrap;
    }
    .parlay-summary-v2 .ps2-stat {
        text-align: center;
    }
    .parlay-summary-v2 .ps2-stat .ps2-label {
        font-size: 0.6rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #8899AA;
        margin-bottom: 0.2rem;
    }
    .parlay-summary-v2 .ps2-stat .ps2-value {
        font-size: 1.2rem;
        font-weight: 800;
        color: #E8EAED;
        font-family: 'JetBrains Mono', monospace;
    }
    .parlay-summary-v2 .ps2-stat .ps2-value.gold {
        color: #FFD700;
    }
    .parlay-summary-v2 .ps2-stat .ps2-value.green {
        color: #00E676;
        text-shadow: 0 0 10px rgba(19,241,149,0.2);
    }

    /* ── Enhanced Parlay Leg Card v2 ── with prob bar ── */
    .parlay-leg-v2 {
        background: rgba(20,23,32,0.8);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: all 0.15s ease, background 0.15s ease;
    }
    .parlay-leg-v2:hover {
        border-color: rgba(0,200,83,0.2);
        background: rgba(26,29,38,0.9);
    }
    .parlay-leg-v2 .leg-left {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .parlay-leg-v2 .leg-num-box {
        width: 36px;
        height: 36px;
        border-radius: 8px;
        background: rgba(0,200,83,0.1);
        border: 1px solid rgba(0,200,83,0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #00C853;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 0.8rem;
        flex-shrink: 0;
    }
    .parlay-leg-v2 .leg-text .leg-name {
        font-size: 0.9rem;
        font-weight: 700;
        color: #E8EAED;
    }
    .parlay-leg-v2 .leg-text .leg-meta {
        font-size: 0.6rem;
        font-weight: 700;
        color: #8899AA;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-top: 0.1rem;
    }
    .parlay-leg-v2 .leg-right {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .parlay-leg-v2 .prob-section {
        text-align: right;
    }
    .parlay-leg-v2 .prob-section .prob-label {
        font-size: 0.6rem;
        font-weight: 700;
        color: #8899AA;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }
    .parlay-leg-v2 .prob-section .prob-value {
        font-size: 0.82rem;
        font-weight: 700;
        color: #E8EAED;
        font-family: 'JetBrains Mono', monospace;
        margin-bottom: 0.25rem;
    }
    .parlay-leg-v2 .prob-bar {
        width: 60px;
        height: 4px;
        background: rgba(255,255,255,0.08);
        border-radius: 2px;
        overflow: hidden;
        margin-left: auto;
    }
    .parlay-leg-v2 .prob-fill {
        height: 100%;
        background: linear-gradient(90deg, #00C853, #00E676);
        border-radius: 2px;
    }
    .parlay-leg-v2 .odds-badge {
        font-size: 1.1rem;
        font-weight: 800;
        color: #00E676;
        font-family: 'JetBrains Mono', monospace;
        min-width: 50px;
        text-align: right;
    }

    /* ── Extend Parlay dashed section ── */
    .extend-parlay {
        background: rgba(13,27,42,0.4);
        border: 2px dashed rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.5rem 1.5rem;
        text-align: center;
        transition: border-color 0.3s ease;
    }
    .extend-parlay:hover {
        border-color: rgba(0,200,83,0.4);
    }
    .extend-parlay .ep-title {
        font-size: 1rem;
        font-weight: 700;
        color: #E8EAED;
        margin-bottom: 0.2rem;
    }
    .extend-parlay .ep-sub {
        font-size: 0.8rem;
        color: #8899AA;
    }

    /* ── Payout Hero display ── */
    .payout-hero {
        text-align: center;
        padding: 1.5rem 1rem;
        background: rgba(20,23,32,0.8);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        box-shadow: inset 0 0 20px rgba(0,200,83,0.05);
    }
    .payout-hero .ph-label {
        font-size: 0.6rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        color: #8899AA;
        margin-bottom: 0.4rem;
    }
    .payout-hero .ph-value {
        font-size: 2.5rem;
        font-weight: 900;
        color: #00E676;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.02em;
        text-shadow: 0 0 30px rgba(0,200,83,0.15);
    }
    .payout-hero .ph-note {
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #8899AA;
        margin-top: 0.4rem;
    }

    /* ── Quick stake buttons ── */
    .stake-btns {
        display: flex;
        gap: 0.4rem;
        margin-top: 0.5rem;
    }
    .stake-btns .qbtn {
        flex: 1;
        text-align: center;
        padding: 0.45rem 0;
        background: rgba(30,35,50,0.8);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 8px;
        color: #E8EAED;
        font-size: 0.75rem;
        font-weight: 700;
        cursor: pointer;
        transition: background 0.15s ease, border-color 0.15s ease;
    }
    .stake-btns .qbtn:hover {
        background: rgba(0,200,83,0.12);
        border-color: rgba(0,200,83,0.3);
    }

    /* ── Odds Alert banner ── */
    .odds-alert-box {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        padding: 0.75rem;
        background: rgba(255,215,0,0.05);
        border: 1px solid rgba(255,215,0,0.2);
        border-radius: 10px;
        margin-bottom: 0.6rem;
    }
    .odds-alert-box .oa-icon {
        color: #FFD700;
        font-size: 1rem;
        flex-shrink: 0;
    }
    .odds-alert-box .oa-text {
        font-size: 0.7rem;
        color: #8899AA;
        line-height: 1.5;
    }
    .odds-alert-box .oa-text .oa-label {
        color: #FFD700;
        font-weight: 700;
    }

    /* ── Place Parlay button ── */
    .place-parlay-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        width: 100%;
        padding: 1rem;
        background: linear-gradient(135deg, #00C853 0%, #00E676 100%);
        color: #0D1B2A;
        font-weight: 900;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        border-radius: 12px;
        border: none;
        cursor: pointer;
        box-shadow: 0 12px 40px -10px rgba(0,200,83,0.4);
        transition: all 0.2s ease;
    }
    .place-parlay-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 16px 48px -10px rgba(0,200,83,0.5);
    }
    .save-fav-btn {
        display: block;
        width: 100%;
        text-align: center;
        padding: 0.7rem;
        background: transparent;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        color: #8899AA;
        font-weight: 700;
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .save-fav-btn:hover {
        background: rgba(255,255,255,0.04);
        border-color: rgba(255,255,255,0.15);
    }

    /* ── Featured Live Match Card ── */
    .featured-live {
        position: relative;
        overflow: hidden;
        border-radius: 16px;
        background: linear-gradient(135deg, #00C853 0%, #05084a 100%);
        padding: 1.4rem 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(0,200,83,0.2);
    }
    .featured-live .fl-badge {
        display: inline-block;
        background: #FF3D3D;
        color: #0D1B2A;
        font-size: 0.6rem;
        font-weight: 900;
        text-transform: uppercase;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        margin-right: 0.5rem;
    }
    .featured-live .fl-time {
        color: rgba(255,255,255,0.7);
        font-size: 0.72rem;
        font-family: 'JetBrains Mono', monospace;
    }
    .featured-live .fl-teams {
        display: flex;
        align-items: center;
        justify-content: space-between;
        max-width: 450px;
        margin: 1rem 0;
    }
    .featured-live .fl-team {
        text-align: center;
    }
    .featured-live .fl-team-icon {
        width: 48px;
        height: 48px;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 0.4rem auto;
        font-size: 1.5rem;
    }
    .featured-live .fl-team-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: #FFFFFF;
    }
    .featured-live .fl-score {
        font-size: 2rem;
        font-weight: 900;
        color: #FFFFFF;
        font-family: 'JetBrains Mono', monospace;
        font-style: italic;
        letter-spacing: -0.02em;
    }
    .featured-live .fl-score-label {
        font-size: 0.6rem;
        font-weight: 600;
        color: rgba(255,255,255,0.7);
        text-transform: uppercase;
        letter-spacing: 0.15em;
        margin-top: 0.2rem;
    }

    /* ── Terminal Top Bar ── */
    .terminal-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: nowrap;
        overflow: hidden;
        background: rgba(13,20,30,0.95);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 16px;
        padding: 0.75rem 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }
    .terminal-topbar .brand {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-shrink: 0;
        white-space: nowrap;
    }
    .terminal-topbar .brand-icon {
        width: 32px;
        height: 32px;
        min-width: 32px;
        background: #00C853;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-size: 1.1rem;
        font-weight: 900;
    }
    .terminal-topbar .brand-text {
        font-size: 1.15rem;
        font-weight: 900;
        color: #E8EAED;
        letter-spacing: -0.01em;
        white-space: nowrap;
    }
    .terminal-topbar .brand-text .accent {
        color: #00C853;
    }
    .terminal-topbar .top-nav {
        display: none;
        align-items: center;
        gap: 1.5rem;
    }
    @media (min-width: 1024px) {
        .terminal-topbar .top-nav { display: flex; }
    }
    .terminal-topbar .top-nav a {
        color: #8899AA;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        text-decoration: none;
        transition: color 0.2s ease;
        cursor: pointer;
    }
    .terminal-topbar .top-nav a:hover {
        color: #E8EAED;
    }
    .terminal-topbar .top-nav a.active {
        color: #00C853;
        border-bottom: 2px solid #00C853;
        padding-bottom: 2px;
    }
    .terminal-topbar .search-wrapper {
        position: relative;
        display: none;
    }
    @media (min-width: 640px) {
        .terminal-topbar .search-wrapper { display: block; }
    }
    .terminal-topbar .search-icon {
        position: absolute;
        left: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
    }
    .terminal-topbar .search-input {
        background: rgba(20,25,38,0.8);
        border: none;
        border-radius: 8px;
        padding: 0.45rem 1rem 0.45rem 2.2rem;
        font-size: 0.8rem;
        color: #E8EAED;
        width: 16rem;
        max-width: 16rem;
        font-family: 'Inter', sans-serif;
        outline: none;
        transition: box-shadow 0.2s ease;
    }
    .terminal-topbar .search-input::placeholder {
        color: #556677;
    }
    .terminal-topbar .search-input:focus {
        box-shadow: 0 0 0 1px rgba(0,200,83,0.5);
    }
    .terminal-topbar .top-right {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .terminal-topbar .live-feed {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.7rem;
        background: rgba(13,27,42,0.7);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
    }
    .terminal-topbar .live-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #00ff88;
        box-shadow: 0 0 8px #00ff88;
        animation: pulse-live 2s ease-in-out infinite;
    }
    @keyframes pulse-live {
        0%, 100% { box-shadow: 0 0 4px #00ff88; }
        50% { box-shadow: 0 0 12px #00ff88, 0 0 20px rgba(0,255,136,0.3); }
    }
    .terminal-topbar .live-text {
        font-size: 0.6rem;
        font-family: 'JetBrains Mono', monospace;
        color: #00ff88;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .terminal-topbar .user-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, #00C853, #40C4FF);
        padding: 2px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .terminal-topbar .user-avatar-inner {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: #0D1420;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #E8EAED;
        font-size: 1rem;
    }

    /* ── Terminal Menu heading ── */
    .terminal-menu-heading {
        font-size: 0.6rem;
        font-weight: 700;
        color: #556677;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        margin-bottom: 0.75rem;
        padding-left: 0.2rem;
    }

    /* ── Subscription Box ── */
    .subscription-box {
        background: rgba(20,23,32,0.85);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 0.9rem 1rem;
        margin-top: 1rem;
    }
    .subscription-box .sub-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }
    .subscription-box .sub-label {
        font-size: 0.6rem;
        font-weight: 700;
        color: #556677;
        text-transform: uppercase;
    }
    .subscription-box .sub-tier {
        font-size: 0.6rem;
        font-weight: 700;
        color: #00ff88;
        background: rgba(0,255,136,0.1);
        border: 1px solid rgba(0,255,136,0.2);
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
    }
    .subscription-box .sub-bar {
        height: 6px;
        width: 100%;
        background: rgba(13,27,42,0.8);
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 0.4rem;
    }
    .subscription-box .sub-bar-fill {
        height: 100%;
        background: #00ff88;
        width: 75%;
        border-radius: 3px;
    }
    .subscription-box .sub-days {
        font-size: 0.68rem;
        color: #8899AA;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------


def render_match_card(
    home: str,
    away: str,
    league: str,
    kickoff: str,
    odds: dict[str, float] | None = None,
) -> str:
    """Return HTML for a single sportsbook-style match card.

    Args:
        home: Home team name.
        away: Away team name.
        league: League / competition label shown in the badge.
        kickoff: ISO kick-off time string displayed on the card.
        odds: Optional mapping of outcome label → best decimal price.
            When provided, an odds-button row is appended below the
            match header. A triangular up/down indicator is shown when
            the price is unusually high or low.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    odds_html = ""
    if odds:
        btns = []
        for label, price in odds.items():
            # Odds movement indicator
            movement = ""
            if price > 2.0:
                movement = ' <span class="odds-up">\u25b2</span>'
            elif price < 1.8:
                movement = ' <span class="odds-down">\u25bc</span>'
            btns.append(
                f'<div class="odds-btn">'
                f'<div class="outcome-label">{label}</div>'
                f'<div class="odds-value">{price:.2f}{movement}</div>'
                f'</div>'
            )
        odds_html = f'<div class="odds-row">{"".join(btns)}</div>'
    return (
        f'<div class="match-card">'
        f'<div class="card-top">'
        f'<span class="league-badge">\u26bd {league}</span>'
        f'<div class="teams">'
        f'<span class="team-name">{home}</span>'
        f'<span class="vs-badge">VS</span>'
        f'<span class="team-name away">{away}</span>'
        f'</div>'
        f'<div class="kickoff">\U0001f550 {kickoff}</div>'
        f'</div>'
        f'{odds_html}'
        f'</div>'
    )


def render_stat_panel(label: str, value: str) -> str:
    """Return HTML for a small glassmorphism stat panel.

    Args:
        label: Short uppercase label displayed above the value.
        value: Formatted value string (e.g. ``"42"`` or ``"5.3%"``).

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    return (
        f'<div class="stat-panel">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'</div>'
    )


def render_slip_card(match: str, outcome: str, odds: float) -> str:
    """Return HTML for a single bet-slip selection card.

    Args:
        match: Match label shown in small muted text above the outcome.
        outcome: Outcome string displayed prominently (e.g. ``"Arsenal"``,
            ``"Over 2.5"``).
        odds: Decimal odds shown in the gold badge on the right.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    return (
        f'<div class="slip-card">'
        f'<div class="slip-info">'
        f'<div class="slip-match">{match}</div>'
        f'<div class="slip-outcome">{outcome}</div>'
        f'</div>'
        f'<div class="slip-odds">{odds:.2f}</div>'
        f'</div>'
    )


def render_value_card(
    home: str,
    away: str,
    outcome: str,
    bookmaker: str,
    price: float,
    edge: float,
    american_odds: str | None = None,
) -> str:
    """Return HTML for a value-bet alert card.

    Args:
        home: Home team name.
        away: Away team name.
        outcome: Outcome being bet (e.g. ``"Home"``, ``"Over 2.5"``).
        bookmaker: Name of the bookmaker offering the value price.
        price: Decimal odds offered by the bookmaker.
        edge: Calculated edge over the consensus probability (0–1 scale).
        american_odds: Optional pre-formatted American odds string
            (e.g. ``"+150"`` or ``"-200"``). When provided, it is shown
            in blue beside the decimal price.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    american_html = (
        f' <span style="font-size:0.7rem;color:#40C4FF;">'
        f"({american_odds})</span>"
        if american_odds
        else ""
    )
    return (
        f'<div class="alert-card">'
        f'<div class="alert-header">'
        f'<span class="alert-teams">\u26bd {home} vs {away}</span>'
        f'<span class="alert-badge badge-value">+{edge:.1%} EDGE</span>'
        f'</div>'
        f'<div class="alert-detail">'
        f'<strong>{outcome}</strong> @ <strong>{price:.2f}</strong>'
        f'{american_html} '
        f'via {bookmaker}'
        f'</div>'
        f'</div>'
    )


def render_arb_card(
    home: str,
    away: str,
    market: str,
    arb_pct: float,
    best_odds: dict,
) -> str:
    """Return HTML for an arbitrage alert card.

    Args:
        home: Home team name.
        away: Away team name.
        market: Market key (e.g. ``"h2h"``, ``"totals"``).
        arb_pct: Guaranteed profit percentage (e.g. ``1.23`` for 1.23%).
        best_odds: Mapping of outcome label → best available decimal price.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    odds_parts = " \u00b7 ".join(f"{k}: <strong>{v:.2f}</strong>" for k, v in best_odds.items())
    return (
        f'<div class="alert-card">'
        f'<div class="alert-header">'
        f'<span class="alert-teams">\U0001f504 {home} vs {away}</span>'
        f'<span class="alert-badge badge-arb">\U0001f4b0 {arb_pct:.3f}% PROFIT</span>'
        f'</div>'
        f'<div class="alert-detail">'
        f'Market: <strong>{market}</strong><br>'
        f'{odds_parts}'
        f'</div>'
        f'</div>'
    )


def render_featured_live_card(
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    minute: str,
    league: str,
) -> str:
    """Return HTML for a featured live match card.

    Renders a gradient-styled card highlighting a live match with
    the current score and minute indicator.

    Args:
        home: Home team name.
        away: Away team name.
        home_score: Current score for the home team.
        away_score: Current score for the away team.
        minute: Match minute string (e.g. ``"74'"``).
        league: League / competition label.

    Returns:
        An HTML string ready for
        ``st.markdown(…, unsafe_allow_html=True)``.
    """
    return (
        f'<div class="featured-live">'
        f'<span class="fl-badge">Live Now</span>'
        f'<span class="fl-time">{minute} - {league}</span>'
        f'<div class="fl-teams">'
        f'<div class="fl-team">'
        f'<div class="fl-team-icon">\U0001f6e1\ufe0f</div>'
        f'<div class="fl-team-name">{home}</div>'
        f'</div>'
        f'<div style="text-align:center;">'
        f'<div class="fl-score">'
        f'{home_score} - {away_score}</div>'
        f'<div class="fl-score-label">Score</div>'
        f'</div>'
        f'<div class="fl-team">'
        f'<div class="fl-team-icon">\U0001f6e1\ufe0f</div>'
        f'<div class="fl-team-name">{away}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def render_payout_hero(
    payout: float,
    stake: float,
) -> str:
    """Return HTML for a large payout display widget.

    Shows the potential payout prominently with a note that
    the displayed amount includes the original stake.

    Args:
        payout: Total potential payout in dollars.
        stake: Original stake amount included in the payout.

    Returns:
        An HTML string ready for
        ``st.markdown(…, unsafe_allow_html=True)``.
    """
    return (
        f'<div class="payout-hero">'
        f'<div class="ph-label">Potential Payout</div>'
        f'<div class="ph-value">${payout:,.2f}</div>'
        f'<div class="ph-note">'
        f'\u2139\ufe0f Includes your ${stake:,.2f} stake'
        f'</div>'
        f'</div>'
    )


def render_parlay_leg(
    index: int,
    label: str,
    odds: float,
    implied_prob: float,
    meta: str = "",
) -> str:
    """Return HTML for an enhanced parlay leg card with probability bar.

    Args:
        index: 1-based leg number shown in the numbered badge.
        label: Human-readable selection label (e.g. ``"Arsenal ML"``).
        odds: Decimal odds for this leg.
        implied_prob: Implied win probability (0–1 scale).
        meta: Optional metadata string shown below the label
            (e.g. ``"Premier League • Today 20:00"``).

    Returns:
        An HTML string ready for
        ``st.markdown(…, unsafe_allow_html=True)``.
    """
    pct = max(0, min(100, round(implied_prob * 100)))
    meta_html = (
        f'<div class="leg-meta">{meta}</div>'
        if meta
        else ""
    )
    return (
        f'<div class="parlay-leg-v2">'
        f'<div class="leg-left">'
        f'<div class="leg-num-box">#{index}</div>'
        f'<div class="leg-text">'
        f'<div class="leg-name">{label}</div>'
        f'{meta_html}'
        f'</div>'
        f'</div>'
        f'<div class="leg-right">'
        f'<div class="prob-section">'
        f'<div class="prob-label">Implied Prob.</div>'
        f'<div class="prob-value">{implied_prob:.1%}</div>'
        f'<div class="prob-bar">'
        f'<div class="prob-fill" style="width:{pct}%"></div>'
        f'</div>'
        f'</div>'
        f'<div class="odds-badge">{odds:.2f}</div>'
        f'</div>'
        f'</div>'
    )


def render_parlay_summary(
    num_legs: int,
    combined_odds: float,
    stake: float,
) -> str:
    """Return HTML for a running parlay summary banner.

    Displays a live summary with a gold accent bar, showing
    the number of legs, combined odds, potential payout,
    and net profit at a glance.

    Args:
        num_legs: Total number of legs currently in the parlay.
        combined_odds: Product of all leg odds (already computed
            upstream).
        stake: Stake amount in dollars used to estimate payout
            and profit.

    Returns:
        An HTML string ready for
        ``st.markdown(…, unsafe_allow_html=True)``.
    """
    payout = stake * combined_odds if combined_odds > 0 else 0
    profit = payout - stake
    return (
        f'<div class="parlay-summary-v2">'
        f'<div class="ps2-tag">Live Summary</div>'
        f'<div class="ps2-title">'
        f'<span class="star">\u2b50</span> Pro Parlay Builder'
        f'</div>'
        f'<div class="ps2-stats">'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Legs</div>'
        f'<div class="ps2-value">{num_legs}</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Combined Odds</div>'
        f'<div class="ps2-value gold">'
        f'{combined_odds:.2f}x</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Total Payout</div>'
        f'<div class="ps2-value green">'
        f'${payout:,.2f}</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Net Profit</div>'
        f'<div class="ps2-value">'
        f'${profit:,.2f}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def _apply_dark_theme(fig):
    """Apply the sportsbook dark theme to a plotly figure."""
    fig.update_layout(
        paper_bgcolor=DARK_THEME["paper_bgcolor"],
        plot_bgcolor=DARK_THEME["plot_bgcolor"],
        font_color=DARK_THEME["font_color"],
        font_family="Inter, sans-serif",
        colorway=DARK_THEME["colorway"],
        title_font_size=14,
        title_font_color="#E8EAED",
        legend_bgcolor="rgba(0,0,0,0)",
        legend_font_color="#8899AA",
    )
    fig.update_xaxes(
        gridcolor=DARK_THEME["gridcolor"],
        zerolinecolor=DARK_THEME["gridcolor"],
        title_font_color="#8899AA",
        tickfont_color="#8899AA",
    )
    fig.update_yaxes(
        gridcolor=DARK_THEME["gridcolor"],
        zerolinecolor=DARK_THEME["gridcolor"],
        title_font_color="#8899AA",
        tickfont_color="#8899AA",
    )
    return fig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@st.cache_resource
def get_db() -> DBManager:
    """Return a cached database manager instance.

    On first run, if the database is empty the demo data seeder is invoked
    automatically so the dashboard has content to display without needing a
    live API key.
    """
    db = DBManager()
    # Auto-seed demo data when the database has no matches yet.
    if not db.get_latest_odds():
        try:
            from src.seed_demo_data import seed  # noqa: WPS433

            seed(db.db_path)
            logger.info("Auto-seeded demo data into %s", db.db_path)
        except Exception:  # noqa: BLE001
            logger.warning("Could not auto-seed demo data.", exc_info=True)
    return db


@st.cache_data(ttl=300)
def load_latest_odds(sport_key: str | None = None) -> pd.DataFrame:
    """Load the latest odds from the database (cached 5 min)."""
    db = get_db()
    rows = db.get_latest_odds(sport_key)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def load_upcoming_matches(sport_key: str | None = None) -> pd.DataFrame:
    """Load upcoming matches from the database (cached 5 min)."""
    db = get_db()
    rows = db.get_upcoming_matches(sport_key)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def compute_summary_stats(
    sport_keys: tuple[str, ...] | None = None,
) -> dict:
    """Compute dashboard KPIs cached for 5 minutes.

    Calculates the headline numbers shown in the summary metrics bar so
    they are not re-derived on every Streamlit re-run.

    Args:
        sport_keys: Optional tuple of sport-key strings to filter by.
            Pass ``None`` to include all leagues.

    Returns:
        Dict with keys ``num_matches``, ``num_value_bets``,
        ``num_arb_opps``.
    """
    db = get_db()
    # Resolve to a single sport_key string for the DB helper (None = all)
    sk = sport_keys[0] if sport_keys and len(sport_keys) == 1 else None
    rows = db.get_latest_odds(sk)
    if not rows:
        return {"num_matches": 0, "num_value_bets": 0, "num_arb_opps": 0}

    df = pd.DataFrame(rows)
    # Filter when multiple sport keys are specified
    if sport_keys and len(sport_keys) > 1:
        df = df[df["sport_key"].isin(sport_keys)]

    num_matches = df["match_id"].nunique() if not df.empty else 0

    _analyzer = OddsAnalyzer()
    try:
        vb = _analyzer.find_value_bets(
            df, sharp_bookmakers=SHARP_BOOKMAKERS, threshold=0.05
        )
        num_value_bets = len(vb) if not vb.empty else 0
    except Exception:
        num_value_bets = 0

    try:
        arb = _analyzer.find_arbitrage(df)
        num_arb_opps = len(arb) if not arb.empty else 0
    except Exception:
        num_arb_opps = 0

    return {
        "num_matches": num_matches,
        "num_value_bets": num_value_bets,
        "num_arb_opps": num_arb_opps,
    }


def fetch_and_store(selected_leagues: list[str]) -> int:
    """Fetch odds from the API and persist them.

    The API key is read from ``st.session_state["api_key_override"]`` first
    so that a user's browser-session key is used without leaking to other
    concurrent sessions via ``os.environ``.

    Args:
        selected_leagues: Display names of leagues to fetch.

    Returns:
        Number of odds rows stored.
    """
    # Use the per-session key override when available (OWASP A07).
    session_key = st.session_state.get("api_key_override") or None
    client = OddsAPIClient(api_key=session_key) if session_key else OddsAPIClient()
    db = get_db()
    all_rows: list[dict] = []
    league_map = {v: k for k, v in LEAGUES.items()}

    for sport_key in selected_leagues:
        league_name = league_map.get(sport_key, sport_key)
        with st.spinner(f"Fetching {league_name}\u2026"):
            rows = client.fetch_odds(sport_key)
            all_rows.extend(rows)

    if all_rows:
        db.store_odds(all_rows)
        # Clear caches so new data is reflected immediately
        load_latest_odds.clear()
        load_upcoming_matches.clear()

    return len(all_rows)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "active_section" not in st.session_state:
    st.session_state["active_section"] = "matches"
if "bet_slip" not in st.session_state:
    st.session_state["bet_slip"] = []
if "parlay_legs" not in st.session_state:
    st.session_state["parlay_legs"] = []
if "last_refreshed" not in st.session_state:
    st.session_state["last_refreshed"] = None

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.markdown(
    """
    <div style="
        background: linear-gradient(135deg, #0D1B2A, #1B2838);
        border: 1px solid rgba(0,200,83,0.15);
        border-radius: 14px;
        padding: 1.2rem 1rem;
        margin-bottom: 1rem;
        text-align: center;
    ">
        <div style="
            width:32px; height:32px;
            background:#00C853; border-radius:8px;
            display:flex; align-items:center;
            justify-content:center; margin:0 auto 0.4rem auto;
            font-size:1.1rem; color:#FFFFFF; font-weight:900;
        "><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="1" y="1" width="10" height="10" rx="2" fill="white"/><rect x="13" y="1" width="10" height="10" rx="2" fill="white"/><rect x="1" y="13" width="10" height="10" rx="2" fill="white"/><rect x="13" y="13" width="10" height="10" rx="2" fill="white"/></svg></div>
        <div style="
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            color: #E8EAED;
            text-transform: uppercase;
        ">APEX<span style="color:#00C853;">ODDS</span> PRO</div>
        <div style="font-size:0.68rem; color:#8899AA; margin-top:0.15rem; letter-spacing:0.05em;">
            VALUE BETS TERMINAL
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("\u2699\ufe0f Settings")

league_options = {name: key for name, key in LEAGUES.items()}
selected_league_names: list[str] = st.sidebar.multiselect(
    "Select Leagues",
    options=list(league_options.keys()),
    default=list(league_options.keys()),
)
selected_sport_keys: list[str] = [
    league_options[n] for n in selected_league_names
]

if st.sidebar.button("\U0001f504 Refresh Data"):
    if not selected_sport_keys:
        st.sidebar.warning("Please select at least one league.")
    else:
        count = fetch_and_store(selected_sport_keys)
        if count:
            st.session_state["last_refreshed"] = pd.Timestamp.now().strftime(
                "%H:%M:%S"
            )
            st.sidebar.success(f"Stored {count} odds rows.")
        else:
            st.sidebar.warning("No data returned. Check your API key.")

# OWASP A07 – allow users to supply an API key override directly in the
# browser UI. The value is stored only in session_state (server RAM) and
# is never written to disk, logs, or the DB.
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<span style='font-size:0.78rem;color:#8899AA;font-weight:600;"
    "text-transform:uppercase;letter-spacing:0.06em;'>"
    "🔑 API Key Override</span>",
    unsafe_allow_html=True,
)
api_key_override = st.sidebar.text_input(
    "API Key (optional)",
    type="password",
    key="sidebar_api_key",
    help=(
        "Enter your The-Odds-API key here to override the .env value. "
        "Stored in session memory only — never persisted to disk."
    ),
    label_visibility="collapsed",
    placeholder="Paste key to override .env…",
)
# Store the override in session_state only.  This is session-scoped and
# does NOT leak to other concurrent users (unlike os.environ).
# OWASP A07 – the key stays in RAM for this browser tab only.
if api_key_override:
    st.session_state["api_key_override"] = api_key_override
    st.sidebar.caption("✅ Key active for this session.")
elif "api_key_override" not in st.session_state:
    st.session_state["api_key_override"] = None

# Last-refresh indicator
if st.session_state.get("last_refreshed"):
    st.sidebar.caption(
        f"🕐 Last refreshed: {st.session_state['last_refreshed']}"
    )

# Subscription status panel – terminal design element
st.sidebar.markdown(
    """
    <div class="subscription-box">
        <div class="sub-header">
            <span class="sub-label">Subscription</span>
            <span class="sub-tier">ELITE</span>
        </div>
        <div class="sub-bar">
            <div class="sub-bar-fill"></div>
        </div>
        <div class="sub-days">12 days remaining</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="terminal-topbar">
        <div class="brand">
            <div class="brand-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <rect x="1" y="1" width="10" height="10" rx="2" fill="white"/>
                    <rect x="13" y="1" width="10" height="10" rx="2" fill="white"/>
                    <rect x="1" y="13" width="10" height="10" rx="2" fill="white"/>
                    <rect x="13" y="13" width="10" height="10" rx="2" fill="white"/>
                </svg>
            </div>
            <div class="brand-text">APEX<span class="accent">ODDS</span> PRO</div>
            <div class="top-nav" style="margin-left: 2rem;">
                <a href="#">Live</a>
                <a class="active" href="#">Value Bets</a>
                <a href="#">Arbitrage</a>
                <a href="#">Calculators</a>
            </div>
        </div>
        <div class="top-right">
            <div class="search-wrapper">
                <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24"
                     fill="none" stroke="#556677" stroke-width="2.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input class="search-input" placeholder="Search markets..." type="text" aria-label="Search markets" />
            </div>
            <div class="live-feed">
                <div class="live-dot"></div>
                <span class="live-text">Live Feed</span>
            </div>
            <div class="user-avatar">
                <div class="user-avatar-inner">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                         stroke="#E8EAED" stroke-width="2" stroke-linecap="round"
                         stroke-linejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-header">
        <div class="hero-title">\u26bd ApexOdds <span class="accent">Pro</span></div>
        <div class="hero-sub">
            VALUE BETS TERMINAL
            <span class="dot"></span>
            REAL-TIME ODDS
            <span class="dot"></span>
            SMART CALCULATORS
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

analyzer = OddsAnalyzer()

# Always load all data from DB, then filter by selected leagues in-app.
odds_df_all = load_latest_odds()
upcoming_df_all = load_upcoming_matches()

if selected_sport_keys and len(selected_sport_keys) < len(LEAGUES):
    odds_df = (
        odds_df_all[odds_df_all["sport_key"].isin(selected_sport_keys)]
        if not odds_df_all.empty
        else odds_df_all
    )
    upcoming_df_base = (
        upcoming_df_all[upcoming_df_all["sport_key"].isin(selected_sport_keys)]
        if not upcoming_df_all.empty
        else upcoming_df_all
    )
else:
    odds_df = odds_df_all
    upcoming_df_base = upcoming_df_all

# ---------------------------------------------------------------------------
# SUMMARY METRICS BAR  (Performance skill – cached computation)
# Clickable cards jump to the corresponding analysis section.
# ---------------------------------------------------------------------------

_sport_key_tuple = tuple(selected_sport_keys) if selected_sport_keys else None
_stats = compute_summary_stats(_sport_key_tuple)

sm_col1, sm_col2, sm_col3, sm_col4 = st.columns(4)
with sm_col1:
    st.metric(
        "📅 Upcoming Matches",
        _stats["num_matches"],
        help="Total matches currently loaded in the database.",
    )
    if st.button("→ View Matches", key="jump_matches", use_container_width=True):
        st.session_state["active_section"] = "matches"
        st.rerun()
with sm_col2:
    st.metric(
        "💡 Value Bets",
        _stats["num_value_bets"],
        help="Bets where bookmaker odds exceed the sharp consensus by ≥5%.",
    )
    if st.button("→ View Value Bets", key="jump_value", use_container_width=True):
        st.session_state["active_section"] = "value"
        st.rerun()
with sm_col3:
    st.metric(
        "🔄 Arb Opportunities",
        _stats["num_arb_opps"],
        help="Markets where the best cross-bookmaker prices sum to <100%.",
    )
    if st.button("→ View Arbitrage", key="jump_arb", use_container_width=True):
        st.session_state["active_section"] = "arb"
        st.rerun()
with sm_col4:
    bookmakers_count = (
        odds_df_all["bookmaker"].nunique() if not odds_df_all.empty else 0
    )
    st.metric(
        "🏦 Bookmakers",
        bookmakers_count,
        help="Number of bookmakers with odds in the current dataset.",
    )
    if st.button("→ View Margins", key="jump_margins", use_container_width=True):
        st.session_state["active_section"] = "margins"
        st.rerun()

st.markdown("<hr style='margin: 0.4rem 0 0.8rem 0;'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# THREE-PANE LAYOUT
# ---------------------------------------------------------------------------

NAV_SECTIONS = [
    ("matches", "\U0001f4c5 Dashboard"),
    ("value", "\U0001f3af Value Bets"),
    ("movement", "\U0001f4c8 Edge Tracker"),
    ("calc", "\U0001f4b0 Bankroll"),
    ("arb", "\U0001f504 Arbitrage"),
    ("margins", "\U0001f4ca Margins"),
    ("parlay", "\U0001f3af Custom Parlay"),
    ("settings", "\U00002699\U0000fe0f Settings"),
]

col_nav, col_main, col_slip = st.columns([2, 5, 3])

# ── Left Navigation Panel ──
with col_nav:
    st.markdown(
        '<div class="terminal-menu-heading">Terminal Menu</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="nav-panel">', unsafe_allow_html=True)
    for key, label in NAV_SECTIONS:
        is_active = st.session_state["active_section"] == key
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                      type="primary" if is_active else "secondary"):
            st.session_state["active_section"] = key
    st.markdown('</div>', unsafe_allow_html=True)

# ── Center Main Pane ──
with col_main:
    active = st.session_state["active_section"]

    # --- Matches ---
    if active == "matches":
        st.subheader("Upcoming Matches")
        upcoming_df = upcoming_df_base

        # Featured live match card (demo / static showcase)
        # Featured live match card — static demo showcase using the first
        # available match.  Real live-score data would require a dedicated
        # live-scores API endpoint (not available from The-Odds-API).
        if not upcoming_df.empty and len(upcoming_df) >= 2:
            first_row = upcoming_df.iloc[0]
            st.markdown(
                render_featured_live_card(
                    home=first_row["home_team"],
                    away=first_row["away_team"],
                    home_score=2,
                    away_score=1,
                    minute="74'",
                    league=first_row.get("league", "Premier League"),
                ),
                unsafe_allow_html=True,
            )

        if upcoming_df.empty:
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-icon">\U0001f4c5</div>'
                '<div class="empty-text">No upcoming matches in the database.<br>'
                'Use <b>Refresh Data</b> in the sidebar to fetch odds.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            # Real-time team search (performance: pure pandas, no extra DB hit)
            team_search = st.text_input(
                "🔍 Search teams…",
                key="match_search",
                placeholder="e.g. Arsenal, Real Madrid",
            )
            if team_search.strip():
                mask = (
                    upcoming_df["home_team"].str.contains(
                        team_search, case=False, na=False
                    )
                    | upcoming_df["away_team"].str.contains(
                        team_search, case=False, na=False
                    )
                )
                upcoming_df = upcoming_df[mask]

            if upcoming_df.empty:
                st.info(f'No matches found for "{team_search}".')
            else:
                st.markdown(
                    f'<span class="count-badge">{len(upcoming_df)} Matches</span>',
                    unsafe_allow_html=True,
                )

                # Build best-odds lookup per match
                best_odds_map: dict[str, dict[str, float]] = {}
                if not odds_df.empty:
                    h2h = odds_df[odds_df["market"] == "h2h"]
                    if not h2h.empty:
                        best = (
                            h2h.groupby(["match_id", "outcome_name"])["outcome_price"]
                            .max()
                            .unstack("outcome_name")
                        )
                        for mid in best.index:
                            row_dict = best.loc[mid].dropna().to_dict()
                            if row_dict:
                                best_odds_map[mid] = row_dict

                # Render cards in a two-column grid
                cols = st.columns(2)
                for idx, (_, row) in enumerate(upcoming_df.iterrows()):
                    m_id = row.get("match_id", "")
                    odds_for_match = best_odds_map.get(m_id)
                    card_html = render_match_card(
                        home=row["home_team"],
                        away=row["away_team"],
                        league=row.get("league", ""),
                        kickoff=str(row["commence_time"]),
                        odds=odds_for_match,
                    )
                    with cols[idx % 2]:
                        st.markdown(card_html, unsafe_allow_html=True)

    # --- Value Bets ---
    elif active == "value":
        st.subheader("Value Bets")
        if odds_df.empty:
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-icon">\U0001f4a1</div>'
                '<div class="empty-text">No odds data available. Refresh data first.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            threshold = st.slider(
                "Minimum edge threshold", 0.01, 0.20, 0.05, 0.01,
                key="value_threshold",
            )
            value_df = analyzer.find_value_bets(
                odds_df, sharp_bookmakers=SHARP_BOOKMAKERS, threshold=threshold
            )
            if value_df.empty:
                st.success(
                    "No value bets found at the current threshold. "
                    "Try lowering the threshold."
                )
            else:
                # Header row: count badge + CSV export (Performance skill)
                badge_col, dl_col = st.columns([3, 1])
                with badge_col:
                    st.markdown(
                        f'<span class="count-badge">{len(value_df)} Value Bets</span>',
                        unsafe_allow_html=True,
                    )
                with dl_col:
                    st.download_button(
                        "📥 Export CSV",
                        data=value_df.to_csv(index=False),
                        file_name="value_bets.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                # Edge distribution histogram (Performance skill – Plotly)
                fig_edge = px.histogram(
                    value_df,
                    x="edge",
                    nbins=15,
                    title="Edge Distribution",
                    labels={"edge": "Edge (probability units)"},
                    color_discrete_sequence=["#00C853"],
                )
                fig_edge.update_layout(bargap=0.08, showlegend=False)
                _apply_dark_theme(fig_edge)
                st.plotly_chart(fig_edge, use_container_width=True)

                # Single BetCalculator instance reused for all rows (Performance)
                _bet_calc_vb = BetCalculator()
                for _, vrow in value_df.iterrows():
                    price = float(vrow.get("outcome_price", 0))
                    # Safely convert to American odds for display alongside decimal
                    try:
                        american = _bet_calc_vb.decimal_to_american(price)
                        american_str: str | None = f"{american:+d}"
                    except (ValueError, ZeroDivisionError):
                        american_str = None

                    card = render_value_card(
                        home=vrow.get("home_team", ""),
                        away=vrow.get("away_team", ""),
                        outcome=vrow.get("outcome_name", ""),
                        bookmaker=vrow.get("bookmaker", ""),
                        price=price,
                        edge=float(vrow.get("edge", 0)),
                        american_odds=american_str,
                    )
                    st.markdown(card, unsafe_allow_html=True)

    # --- Arbitrage ---
    elif active == "arb":
        st.subheader("Arbitrage Opportunities")
        if odds_df.empty:
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-icon">\U0001f504</div>'
                '<div class="empty-text">No odds data available. Refresh data first.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            arb_df = analyzer.find_arbitrage(odds_df)
            if arb_df.empty:
                st.success("No arbitrage opportunities found in current data.")
            else:
                # Header row: count badge + CSV export
                arb_badge_col, arb_dl_col = st.columns([3, 1])
                with arb_badge_col:
                    st.markdown(
                        f'<span class="count-badge">{len(arb_df)} Opportunities</span>',
                        unsafe_allow_html=True,
                    )
                with arb_dl_col:
                    st.download_button(
                        "📥 Export CSV",
                        data=arb_df.drop(columns=["best_odds"], errors="ignore")
                        .to_csv(index=False),
                        file_name="arbitrage.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                for _, arow in arb_df.iterrows():
                    card = render_arb_card(
                        home=arow["home_team"],
                        away=arow["away_team"],
                        market=arow["market"],
                        arb_pct=float(arow["arb_pct"]),
                        best_odds=arow["best_odds"],
                    )
                    st.markdown(card, unsafe_allow_html=True)

    # --- Movement ---
    elif active == "movement":
        st.subheader("Odds Movement")
        upcoming_df2 = upcoming_df_base

        if upcoming_df2.empty:
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-icon">\U0001f4c8</div>'
                '<div class="empty-text">No matches in the database.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            match_labels = {
                f"{r['home_team']} vs {r['away_team']}": r["match_id"]
                for _, r in upcoming_df2.iterrows()
            }
            selected_match_label = st.selectbox(
                "Select Match", options=list(match_labels.keys())
            )
            selected_match_id = match_labels[selected_match_label]

            db2 = get_db()
            history = db2.get_odds_history(selected_match_id)
            hist_df = pd.DataFrame(history)

            if hist_df.empty:
                st.info("No historical odds for this match yet.")
            else:
                bookmakers = sorted(hist_df["bookmaker"].unique())
                # Multi-bookmaker comparison overlay (UX improvement)
                selected_books = st.multiselect(
                    "Compare Bookmakers",
                    options=bookmakers,
                    default=bookmakers[:1],
                    help=(
                        "Select one or more bookmakers to overlay their "
                        "price movements on the same chart."
                    ),
                )

                if not selected_books:
                    st.info("Select at least one bookmaker to display the chart.")
                else:
                    filtered = hist_df[
                        (hist_df["bookmaker"].isin(selected_books))
                        & (hist_df["market"] == "h2h")
                    ]

                    if filtered.empty:
                        st.info("No h2h odds history for the selected bookmakers.")
                    else:
                        # Avoid a full copy — assign the new column directly
                        filtered = filtered.assign(
                            series=(
                                filtered["bookmaker"]
                                + " – "
                                + filtered["outcome_name"]
                            )
                        )
                        fig = px.line(
                            filtered,
                            x="timestamp",
                            y="outcome_price",
                            color="series",
                            title=(
                                f"Odds Movement – "
                                f"{', '.join(selected_books)}"
                            ),
                            labels={
                                "timestamp": "Time",
                                "outcome_price": "Decimal Odds",
                                "series": "Bookmaker – Outcome",
                            },
                            markers=True,
                        )
                        _apply_dark_theme(fig)
                        st.plotly_chart(fig, use_container_width=True)

    # --- Margins ---
    elif active == "margins":
        st.subheader("Bookmaker Margin Analysis")
        if odds_df.empty:
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-icon">\U0001f4ca</div>'
                '<div class="empty-text">No odds data available. Refresh data first.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            h2h_df = odds_df[odds_df["market"] == "h2h"]
            if h2h_df.empty:
                st.info("No 1X2 odds data available.")
            else:
                margins: list[dict] = []
                for (match_id, bookmaker), grp in h2h_df.groupby(
                    ["match_id", "bookmaker"]
                ):
                    prices = grp["outcome_price"].tolist()
                    if len(prices) >= 2:  # noqa: PLR2004
                        try:
                            margin = analyzer.calculate_margin(prices)
                            margins.append(
                                {
                                    "bookmaker": bookmaker,
                                    "margin": margin * 100,
                                }
                            )
                        except ValueError:
                            continue

                if margins:
                    margin_df = pd.DataFrame(margins)
                    avg_margin = (
                        margin_df.groupby("bookmaker")["margin"]
                        .mean()
                        .reset_index()
                        .sort_values("margin")
                    )

                    fig_bar = px.bar(
                        avg_margin,
                        x="bookmaker",
                        y="margin",
                        title="Average Bookmaker Margin (%) \u2013 1X2 Markets",
                        labels={
                            "bookmaker": "Bookmaker",
                            "margin": "Avg Margin (%)",
                        },
                        color="margin",
                        color_continuous_scale="RdYlGn_r",
                    )
                    fig_bar.update_layout(showlegend=False)
                    _apply_dark_theme(fig_bar)
                    st.plotly_chart(fig_bar, use_container_width=True)

                    # Sortable detail table (Performance skill – no recompute)
                    st.markdown("##### Margin Detail Table")
                    display_tbl = avg_margin.rename(
                        columns={"bookmaker": "Bookmaker", "margin": "Avg Margin (%)"}
                    ).copy()
                    display_tbl["Avg Margin (%)"] = display_tbl[
                        "Avg Margin (%)"
                    ].round(3)
                    st.dataframe(
                        display_tbl,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Avg Margin (%)": st.column_config.NumberColumn(
                                format="%.3f%%"
                            )
                        },
                    )
                else:
                    st.info("Insufficient data to compute margins.")

    # --- Bet Calculator ---
    elif active == "calc":
        st.subheader("\U0001f9ee Bet Calculator")

        calc_mode = st.radio(
            "Mode",
            ["Calculator Tools", "Bet Builder"],
            horizontal=True,
            key="calc_mode",
        )

        if calc_mode == "Bet Builder":
            st.markdown(
                "Pick outcomes from available matches and build a single bet or "
                "accumulator with real odds."
            )

            bet_calc_builder = BetCalculator()

            if odds_df.empty:
                st.info(
                    "No odds data available. Use **Refresh Data** in the sidebar "
                    "to fetch odds first."
                )
            else:
                h2h_builder = odds_df[odds_df["market"] == "h2h"]
                if h2h_builder.empty:
                    st.info("No 1X2 odds available to build bets from.")
                else:
                    # Build match labels
                    match_info = (
                        h2h_builder[["match_id", "home_team", "away_team", "league"]]
                        .drop_duplicates("match_id")
                        .reset_index(drop=True)
                    )
                    match_info["label"] = (
                        match_info["home_team"]
                        + " vs "
                        + match_info["away_team"]
                        + " ("
                        + match_info["league"]
                        + ")"
                    )
                    label_to_id = dict(
                        zip(match_info["label"], match_info["match_id"])
                    )

                    st.markdown("#### Add a Selection")
                    col_m, col_o, col_b = st.columns([3, 2, 2])
                    with col_m:
                        sel_match_label = st.selectbox(
                            "Match",
                            options=list(label_to_id.keys()),
                            key="builder_match",
                        )
                    sel_match_id = label_to_id.get(sel_match_label, "")

                    # Available outcomes for selected match
                    match_h2h = h2h_builder[h2h_builder["match_id"] == sel_match_id]
                    outcomes = sorted(match_h2h["outcome_name"].unique())
                    bookmakers = sorted(match_h2h["bookmaker"].unique())

                    with col_o:
                        sel_outcome = st.selectbox(
                            "Outcome", options=outcomes, key="builder_outcome"
                        )
                    with col_b:
                        sel_bookmaker = st.selectbox(
                            "Bookmaker", options=bookmakers, key="builder_book"
                        )

                    # Find the specific odds row
                    specific = match_h2h[
                        (match_h2h["outcome_name"] == sel_outcome)
                        & (match_h2h["bookmaker"] == sel_bookmaker)
                    ]
                    if not specific.empty:
                        sel_odds = float(specific.iloc[0]["outcome_price"])
                        st.markdown(
                            f"**Selected odds:** `{sel_odds:.2f}` "
                            f"({sel_outcome} @ {sel_bookmaker})"
                        )
                    else:
                        sel_odds = None
                        st.warning("No odds found for this combination.")

                    if st.button("\u2795 Add to Bet Slip", key="btn_add_slip"):
                        if sel_odds is not None and sel_odds > 1.0:
                            st.session_state["bet_slip"].append(
                                {
                                    "match": sel_match_label,
                                    "outcome": sel_outcome,
                                    "bookmaker": sel_bookmaker,
                                    "decimal_odds": sel_odds,
                                }
                            )
                            st.success(
                                f"Added: {sel_outcome} ({sel_match_label}) "
                                f"@ {sel_odds:.2f}"
                            )
                        else:
                            st.error("Cannot add \u2014 no valid odds selected.")

            # --- Bet Slip Display (inline in calc pane) ---
            st.markdown("---")
            st.markdown("#### \U0001f5d2\ufe0f Your Bet Slip")
            slip = st.session_state["bet_slip"]

            if not slip:
                st.info("Your bet slip is empty. Add selections above.")
            else:
                for sel in slip:
                    st.markdown(
                        render_slip_card(
                            match=sel.get("match", ""),
                            outcome=sel.get("outcome", ""),
                            odds=sel["decimal_odds"],
                        ),
                        unsafe_allow_html=True,
                    )

                col_type, col_stake = st.columns(2)
                with col_type:
                    builder_bet_type = st.radio(
                        "Bet Type",
                        ["Single (each selection)", "Accumulator (combined)"],
                        key="builder_bet_type",
                        horizontal=True,
                    )
                with col_stake:
                    builder_stake = st.number_input(
                        "Stake ($)", min_value=0.0, value=10.0, step=5.0,
                        key="builder_stake",
                    )

                col_calc, col_clear = st.columns(2)
                with col_calc:
                    if st.button("\U0001f4b0 Calculate Payout", key="btn_calc_slip"):
                        bt = (
                            "single"
                            if builder_bet_type.startswith("Single")
                            else "accumulator"
                        )
                        result = bet_calc_builder.build_bet_slip(
                            slip, builder_stake, bet_type=bt,
                        )
                        st.markdown("##### Results")
                        r1, r2, r3 = st.columns(3)
                        r1.metric("Combined Odds", f"{result['combined_odds']:.4f}")
                        r2.metric("Total Payout", f"${result['total_payout']:.2f}")
                        r3.metric("Total Profit", f"${result['total_profit']:.2f}")

                        if bt == "accumulator":
                            st.caption(
                                "Accumulator: all selections must win for a payout."
                            )
                        else:
                            st.caption(
                                "Single: stake is placed on each selection independently."
                            )
                with col_clear:
                    if st.button("\U0001f5d1\ufe0f Clear Bet Slip", key="btn_clear_slip"):
                        st.session_state["bet_slip"] = []
                        st.rerun()

        else:  # Calculator Tools
            bet_calc = BetCalculator()

            calc_section = st.radio(
                "Select Calculator",
                [
                    "Single Bet",
                    "Accumulator / Parlay",
                    "Odds Converter",
                    "Kelly Criterion",
                    "Dutching",
                ],
                horizontal=True,
                key="calc_section",
            )

            # --- Single Bet ---
            if calc_section == "Single Bet":
                st.markdown("#### Single Bet Payout")
                col1, col2 = st.columns(2)
                with col1:
                    sb_stake = st.number_input(
                        "Stake", min_value=0.0, value=100.0, step=10.0,
                        key="sb_stake",
                    )
                with col2:
                    sb_odds = st.number_input(
                        "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                        key="sb_odds",
                    )
                if st.button("Calculate Payout", key="btn_single"):
                    result = bet_calc.calculate_payout(sb_stake, sb_odds)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Payout", f"${result['payout']:.2f}")
                    c2.metric("Profit", f"${result['profit']:.2f}")
                    c3.metric("Implied Probability", f"{result['implied_probability']:.2%}")

            # --- Accumulator / Parlay ---
            elif calc_section == "Accumulator / Parlay":
                st.markdown("#### Accumulator / Parlay Calculator")
                acc_stake = st.number_input(
                    "Stake", min_value=0.0, value=10.0, step=5.0,
                    key="acc_stake",
                )
                num_legs = st.number_input(
                    "Number of Legs", min_value=2, max_value=20, value=3, step=1,
                    key="acc_legs",
                )
                leg_odds: list[float] = []
                cols = st.columns(min(int(num_legs), 5))
                for i in range(int(num_legs)):
                    with cols[i % len(cols)]:
                        val = st.number_input(
                            f"Leg {i + 1} Odds", min_value=1.01, value=2.0, step=0.05,
                            key=f"acc_leg_{i}",
                        )
                        leg_odds.append(val)
                if st.button("Calculate Accumulator", key="btn_acc"):
                    result = bet_calc.calculate_accumulator(acc_stake, leg_odds)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Combined Odds", f"{result['combined_odds']:.4f}")
                    c2.metric("Payout", f"${result['payout']:.2f}")
                    c3.metric("Profit", f"${result['profit']:.2f}")
                    c4.metric("Implied Prob.", f"{result['implied_probability']:.4%}")

            # --- Odds Converter ---
            elif calc_section == "Odds Converter":
                st.markdown("#### Odds Format Converter")
                fmt = st.selectbox(
                    "Input Format",
                    ["Decimal", "American", "Fractional"],
                    key="odds_fmt",
                )
                if fmt == "Decimal":
                    dec = st.number_input(
                        "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                        key="conv_dec",
                    )
                    if st.button("Convert", key="btn_conv"):
                        num, den = bet_calc.decimal_to_fractional(dec)
                        american = bet_calc.decimal_to_american(dec)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Decimal", f"{dec:.2f}")
                        c2.metric("Fractional", f"{num}/{den}")
                        c3.metric("American", f"{american:+d}")
                elif fmt == "American":
                    amer = st.number_input(
                        "American Odds", value=150, step=10, key="conv_amer",
                    )
                    if amer == 0:
                        st.warning("American odds cannot be zero.")
                    elif st.button("Convert", key="btn_conv_a"):
                        dec = bet_calc.american_to_decimal(int(amer))
                        num, den = bet_calc.decimal_to_fractional(dec)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Decimal", f"{dec:.4f}")
                        c2.metric("Fractional", f"{num}/{den}")
                        c3.metric("American", f"{int(amer):+d}")
                else:  # Fractional
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        fnum = st.number_input(
                            "Numerator", min_value=1, value=3, step=1,
                            key="conv_fnum",
                        )
                    with fc2:
                        fden = st.number_input(
                            "Denominator", min_value=1, value=2, step=1,
                            key="conv_fden",
                        )
                    if st.button("Convert", key="btn_conv_f"):
                        dec = bet_calc.fractional_to_decimal(int(fnum), int(fden))
                        american = bet_calc.decimal_to_american(dec)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Decimal", f"{dec:.4f}")
                        c2.metric("Fractional", f"{int(fnum)}/{int(fden)}")
                        c3.metric("American", f"{american:+d}")

            # --- Kelly Criterion ---
            elif calc_section == "Kelly Criterion":
                st.markdown("#### Kelly Criterion Stake Calculator")
                kc1, kc2 = st.columns(2)
                with kc1:
                    kc_odds = st.number_input(
                        "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                        key="kc_odds",
                    )
                    kc_prob = st.slider(
                        "Estimated Win Probability",
                        0.01, 0.99, 0.50, 0.01,
                        key="kc_prob",
                    )
                with kc2:
                    kc_bankroll = st.number_input(
                        "Bankroll", min_value=1.0, value=1000.0, step=50.0,
                        key="kc_bankroll",
                    )
                    kc_frac = st.slider(
                        "Kelly Fraction (1 = full Kelly)",
                        0.1, 1.0, 0.5, 0.1,
                        key="kc_frac",
                    )
                if st.button("Calculate Kelly Stake", key="btn_kelly"):
                    result = bet_calc.kelly_criterion(
                        kc_odds, kc_prob, kc_bankroll, kc_frac
                    )
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Edge", f"{result['edge']:.2%}")
                    c2.metric("Kelly Fraction", f"{result['kelly_fraction']:.4f}")
                    c3.metric(
                        "Recommended Stake",
                        f"${result['recommended_stake']:.2f}",
                    )
                    if result["edge"] <= 0:
                        st.warning(
                            "\u26a0\ufe0f No positive edge detected \u2014 Kelly recommends no bet."
                        )

            # --- Dutching ---
            else:
                st.markdown("#### Dutching Calculator")
                dt_stake = st.number_input(
                    "Total Stake", min_value=1.0, value=100.0, step=10.0,
                    key="dt_stake",
                )
                dt_num = st.number_input(
                    "Number of Selections", min_value=2, max_value=10, value=3, step=1,
                    key="dt_num",
                )
                dt_odds: list[float] = []
                cols_dt = st.columns(min(int(dt_num), 5))
                for i in range(int(dt_num)):
                    with cols_dt[i % len(cols_dt)]:
                        val = st.number_input(
                            f"Selection {i + 1} Odds",
                            min_value=1.01, value=3.00, step=0.10,
                            key=f"dt_odds_{i}",
                        )
                        dt_odds.append(val)
                if st.button("Calculate Dutching", key="btn_dutch"):
                    result = bet_calc.dutching_calculator(dt_stake, dt_odds)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Equal Payout", f"${result['equal_payout']:.2f}")
                    c2.metric("Profit", f"${result['profit']:.2f}")
                    c3.metric("Market Margin", f"{result['margin']:.2%}")
                    st.markdown("**Individual Stakes:**")
                    stake_data = {
                        f"Selection {i + 1} (@ {dt_odds[i]:.2f})": f"${s:.2f}"
                        for i, s in enumerate(result["stakes"])
                    }
                    st.json(stake_data)

    # --- Custom Bet & Parlay Calculator ---
    elif active == "parlay":
        st.subheader("\U0001f3af Custom Parlay Builder")

        parlay_calc = BetCalculator()
        legs = st.session_state["parlay_legs"]

        # --- Running Parlay Summary (always visible when legs exist) ---
        if legs:
            odds_list = [lg["decimal_odds"] for lg in legs]
            combined = 1.0
            for o in odds_list:
                combined *= o
            combined = round(combined, 4)
            summary_stake = st.session_state.get("parlay_stake", 10.0)
            st.markdown(
                render_parlay_summary(len(legs), combined, summary_stake),
                unsafe_allow_html=True,
            )

        # --- Display legs with remove buttons ---
        legs = st.session_state["parlay_legs"]

        if not legs:
            st.markdown(
                '<div class="empty-state">'
                '<div class="empty-icon">\U0001f3af</div>'
                '<div class="empty-text">No selections added yet.<br>'
                'Build your parlay by adding picks below.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span style='font-size:0.78rem;color:#8899AA;"
                "font-weight:700;text-transform:uppercase;"
                "letter-spacing:0.15em;'>Selected Legs</span>",
                unsafe_allow_html=True,
            )

            # Render each leg with a remove button
            for i, lg in enumerate(legs):
                leg_col, rm_col = st.columns([8, 1])
                with leg_col:
                    prob = 1.0 / lg["decimal_odds"]
                    st.markdown(
                        render_parlay_leg(
                            i + 1,
                            lg["label"],
                            lg["decimal_odds"],
                            prob,
                        ),
                        unsafe_allow_html=True,
                    )
                with rm_col:
                    if st.button(
                        "\u2716",
                        key=f"rm_leg_{i}",
                        help=f"Remove {lg['label']}",
                    ):
                        st.session_state["parlay_legs"].pop(i)
                        st.rerun()

            # --- Clear all button ---
            if st.button(
                "\U0001f5d1\ufe0f Clear All Picks",
                key="btn_clear_parlay",
            ):
                st.session_state["parlay_legs"] = []
                st.rerun()

        # --- Extend your parlay (Add a leg) ---
        st.markdown(
            '<div class="extend-parlay">'
            '<div class="ep-title">Extend your parlay</div>'
            '<div class="ep-sub">'
            "Add another selection to increase your potential payout"
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        pc1, pc2 = st.columns([3, 3])
        with pc1:
            parlay_label = st.text_input(
                "Selection (e.g. Arsenal ML, Over 2.5 Goals)",
                key="parlay_label",
                placeholder="Selection Name (e.g., Liverpool ML)",
            )
        with pc2:
            parlay_odds_fmt = st.selectbox(
                "Odds format",
                ["Decimal", "American", "Fractional"],
                key="parlay_odds_fmt",
            )

        if parlay_odds_fmt == "Decimal":
            parlay_dec = st.number_input(
                "Decimal Odds", min_value=1.01, value=2.00, step=0.05,
                key="parlay_dec",
            )
        elif parlay_odds_fmt == "American":
            parlay_amer = st.number_input(
                "American Odds", value=150, step=10,
                key="parlay_amer",
            )
            parlay_dec = (
                parlay_calc.american_to_decimal(int(parlay_amer))
                if parlay_amer != 0
                else 2.0
            )
        else:
            pf1, pf2 = st.columns(2)
            with pf1:
                parlay_num = st.number_input(
                    "Numerator", min_value=1, value=3, step=1,
                    key="parlay_fnum",
                )
            with pf2:
                parlay_den = st.number_input(
                    "Denominator", min_value=1, value=2, step=1,
                    key="parlay_fden",
                )
            parlay_dec = parlay_calc.fractional_to_decimal(
                int(parlay_num), int(parlay_den)
            )

        implied = 1.0 / parlay_dec if parlay_dec > 0 else 0
        st.markdown(
            f"**Odds:** `{parlay_dec:.4f}` · "
            f"**Implied probability:** `{implied:.1%}`"
        )

        if st.button("\u2795 Add Leg", key="btn_add_parlay_leg"):
            label = parlay_label.strip() or f"Leg {len(legs) + 1}"
            if parlay_dec > 1.0:
                st.session_state["parlay_legs"].append(
                    {
                        "label": label,
                        "decimal_odds": round(parlay_dec, 4),
                    }
                )
                st.success(f"Added: **{label}** @ {parlay_dec:.4f}")
            else:
                st.error("Odds must be greater than 1.0.")

            # --- Calculation options ---
            st.markdown("---")
            st.markdown("#### Calculate Payout")

            parlay_mode = st.radio(
                "Bet type",
                ["Straight Parlay", "Round-Robin", "Singles"],
                horizontal=True,
                key="parlay_mode",
            )

            parlay_stake = st.number_input(
                "Stake ($)", min_value=0.0, value=10.0, step=5.0,
                key="parlay_stake",
            )

            odds_list = [lg["decimal_odds"] for lg in legs]

            if parlay_mode == "Straight Parlay":
                if st.button("\U0001f4b0 Calculate Parlay", key="btn_calc_parlay"):
                    result = parlay_calc.calculate_accumulator(parlay_stake, odds_list)
                    # Payout display box
                    st.markdown(
                        f'<div class="parlay-payout-box">'
                        f'<div class="payout-label">Total Payout (All Legs Win)</div>'
                        f'<div class="payout-value">${result["payout"]:.2f}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Combined Odds", f"{result['combined_odds']:.4f}")
                    r2.metric("Profit", f"${result['profit']:.2f}")
                    r3.metric("Implied Prob.", f"{result['implied_probability']:.4%}")
                    st.caption(
                        "All legs must win for a payout."
                    )

            elif parlay_mode == "Round-Robin":
                max_combo = len(legs)
                combo_size = st.slider(
                    "Legs per combo",
                    min_value=2,
                    max_value=max(max_combo, 2),
                    value=min(2, max_combo),
                    key="rr_combo_size",
                )
                if combo_size > len(legs):
                    st.warning("Combo size cannot exceed the number of legs.")
                elif st.button("\U0001f4b0 Calculate Round-Robin", key="btn_calc_rr"):
                    result = parlay_calc.calculate_round_robin(
                        parlay_stake, odds_list, combo_size
                    )
                    # Payout display box
                    st.markdown(
                        f'<div class="parlay-payout-box">'
                        f'<div class="payout-label">Total Payout (All Legs Win)</div>'
                        f'<div class="payout-value">${result["total_payout_all_win"]:.2f}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Parlays", result["num_combos"])
                    r2.metric("Total Staked", f"${result['total_staked']:.2f}")
                    r3.metric("Profit (all win)", f"${result['total_profit_all_win']:.2f}")

                    st.markdown("##### Individual Parlays")
                    for idx, combo in enumerate(result["combos"], 1):
                        combo_labels = [legs[i]["label"] for i in combo["legs"]]
                        with st.expander(
                            f"Parlay {idx}: {' + '.join(combo_labels)}  "
                            f"\u2014 Odds {combo['combined_odds']:.4f}  "
                            f"\u2192 ${combo['payout']:.2f}"
                        ):
                            for i in combo["legs"]:
                                st.markdown(
                                    f"- **{legs[i]['label']}** @ {legs[i]['decimal_odds']:.2f}"
                                )

            else:  # Singles
                if st.button("\U0001f4b0 Calculate Singles", key="btn_calc_singles"):
                    st.markdown("##### Single-Bet Payouts")
                    total_payout = 0.0
                    for i, lg in enumerate(legs):
                        res = parlay_calc.calculate_payout(parlay_stake, lg["decimal_odds"])
                        total_payout += res["payout"]
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.markdown(f"**{lg['label']}** @ {lg['decimal_odds']:.2f}")
                        c2.metric("Payout", f"${res['payout']:.2f}")
                        c3.metric("Profit", f"${res['profit']:.2f}")
                    total_staked = parlay_stake * len(legs)
                    st.markdown("---")
                    s1, s2 = st.columns(2)
                    s1.metric("Total Staked", f"${total_staked:.2f}")
                    s2.metric("Total Payout (all win)", f"${total_payout:.2f}")

    # --- Settings ---
    elif active == "settings":
        st.subheader("Settings")
        st.markdown(
            '<div class="alert-card">'
            '<div class="alert-header">'
            '<span class="alert-teams">'
            "\u2699\ufe0f Application Settings</span>"
            "</div>"
            '<div class="alert-detail">'
            "Use the <strong>sidebar panel</strong> on the left "
            "to configure leagues, refresh data, and manage your "
            "API key override."
            "</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown("##### League Selection")
        st.info(
            "Open the sidebar (**⚙️ Settings**) to select which "
            "leagues to monitor and to refresh odds data."
        )

        st.markdown("##### API Key")
        st.info(
            "Your API key is session-scoped and stored in memory "
            "only. Paste it in the sidebar **🔑 API Key Override** "
            "field. It is never written to disk or logs."
        )

        st.markdown("##### Subscription")
        st.markdown(
            '<div class="subscription-box">'
            '<div class="sub-header">'
            '<span class="sub-label">Subscription</span>'
            '<span class="sub-tier">ELITE</span>'
            "</div>"
            '<div class="sub-bar">'
            '<div class="sub-bar-fill"></div>'
            "</div>"
            '<div class="sub-days">12 days remaining</div>'
            "</div>",
            unsafe_allow_html=True,
        )

# ── Right Pane: Persistent Bet Slip ──
with col_slip:
    st.markdown(
        "<span style='font-size:0.7rem;color:#8899AA;"
        "font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.15em;'>Bet Slip Summary</span>",
        unsafe_allow_html=True,
    )

    slip = st.session_state["bet_slip"]
    parlay_legs_list = st.session_state["parlay_legs"]

    has_items = bool(slip) or bool(parlay_legs_list)

    if slip:
        st.markdown("**Bet Builder Selections**")
        for sel in slip:
            st.markdown(
                render_slip_card(
                    match=sel.get("match", ""),
                    outcome=sel.get("outcome", ""),
                    odds=sel["decimal_odds"],
                ),
                unsafe_allow_html=True,
            )

    if parlay_legs_list:
        st.markdown("**Custom Parlay Legs**")
        for lg in parlay_legs_list:
            st.markdown(
                render_slip_card(
                    match="Custom Selection",
                    outcome=lg["label"],
                    odds=lg["decimal_odds"],
                ),
                unsafe_allow_html=True,
            )

    if not has_items:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f3ab</div>'
            '<div class="empty-text">Your bet slip is empty.<br>'
            'Add selections from Bet Builder or Custom Parlay.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        all_odds = [s["decimal_odds"] for s in slip] + [
            lg["decimal_odds"] for lg in parlay_legs_list
        ]

        # --- Payout hero display ---
        _live_calc = BetCalculator()
        slip_stake = st.session_state.get("slip_pane_stake", 100.0)
        if len(all_odds) == 1:
            _res = _live_calc.calculate_payout(slip_stake, all_odds[0])
        elif len(all_odds) > 1:
            _res = _live_calc.calculate_accumulator(
                slip_stake, all_odds,
            )
        else:
            _res = {"payout": 0.0, "profit": 0.0}

        st.markdown(
            render_payout_hero(_res["payout"], slip_stake),
            unsafe_allow_html=True,
        )

        # --- Stake input ---
        st.markdown(
            "<span style='font-size:0.82rem;font-weight:700;"
            "color:#E8EAED;'>Enter Stake</span>",
            unsafe_allow_html=True,
        )
        slip_stake = st.number_input(
            "Stake ($)",
            min_value=0.0,
            value=100.0,
            step=5.0,
            key="slip_pane_stake",
            label_visibility="collapsed",
        )

        # Quick-add stake buttons (functional Streamlit buttons)
        qs_cols = st.columns(4)
        with qs_cols[0]:
            if st.button("+10", key="qs_10", use_container_width=True):
                st.session_state["slip_pane_stake"] = slip_stake + 10
                st.rerun()
        with qs_cols[1]:
            if st.button("+50", key="qs_50", use_container_width=True):
                st.session_state["slip_pane_stake"] = slip_stake + 50
                st.rerun()
        with qs_cols[2]:
            if st.button("+100", key="qs_100", use_container_width=True):
                st.session_state["slip_pane_stake"] = slip_stake + 100
                st.rerun()
        with qs_cols[3]:
            if st.button("MAX", key="qs_max", use_container_width=True):
                st.session_state["slip_pane_stake"] = 1000.0
                st.rerun()

        # --- Odds alert (informational) ---
        if parlay_legs_list:
            st.markdown(
                '<div class="odds-alert-box">'
                '<span class="oa-icon">\u26a0\ufe0f</span>'
                '<div class="oa-text">'
                '<span class="oa-label">Odds Alert:</span> '
                "Markets may shift while you are building. "
                "Review odds before placing."
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        # --- Live payout metrics ---
        if len(all_odds) == 1:
            st.metric("Payout", f"${_res['payout']:.2f}")
            st.metric("Profit", f"${_res['profit']:.2f}")
        elif len(all_odds) > 1:
            st.metric(
                "Combined Odds",
                f"{_res['combined_odds']:.4f}",
                help="Product of all selected decimal odds.",
            )
            st.metric("Total Profit", f"${_res['profit']:.2f}")
            st.caption(
                f"{len(all_odds)} selections \u00b7 "
                f"Implied prob: "
                f"{_res['implied_probability']:.2%}"
            )

        # --- Place Parlay / Save to Favorites actions ---
        if st.button(
            "\u26a1 Place Parlay",
            key="btn_place_parlay",
            use_container_width=True,
            type="primary",
        ):
            st.success(
                "\u2705 Parlay placed! (demo mode — no real wager)"
            )
        if st.button(
            "Save to Favorites",
            key="btn_save_fav",
            use_container_width=True,
        ):
            st.info(
                "\u2b50 Parlay saved to favorites! (demo mode)"
            )

        st.markdown("")  # spacer

        if st.button(
            "\U0001f5d1\ufe0f Clear All",
            key="btn_slip_pane_clear",
        ):
            st.session_state["bet_slip"] = []
            st.session_state["parlay_legs"] = []
            st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="app-footer">
        \u26bd ApexOdds Pro \u00b7 Built with
        <span class="footer-accent">Streamlit</span> \u00b7
        Value Bets Terminal
    </div>
    """,
    unsafe_allow_html=True,
)
