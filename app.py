import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# -- Mobile Friendly page layout --
st.set_page_config(
    page_title="Mutual Fund Comparison Tool",
    layout="wide"
)

st.markdown("""
    <style>
    /* Change button hover color to green */
    button:hover {
        color: #ffffff !important;
        background-color: #28a745 !important;
    }

    /* Change selectbox hover border to green */
    div[data-baseweb="select"] > div:hover {
        border-color: #28a745 !important;
    }

    /* Also tweak focus ring color (when dropdown is selected) */
    div[data-baseweb="select"] > div:focus-within {
        border-color: #28a745 !important;
        box-shadow: 0 0 0 1px #28a745 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Load fund list ---
@st.cache_data
def load_fund_list():
    df = pd.read_excel("fund_urls.xlsx")
    df = df.dropna(subset=["Fund Name", "URL"])
    df["Fund Name"] = df["Fund Name"].str.strip()
    df["URL"] = df["URL"].str.strip()
    return df

df_urls = load_fund_list()

# -- Keeps the hover over color to Blue
st.markdown("""
    <style>
    /* Change hover text color inside the expander title */
    [data-testid="stExpander"] summary:hover span {
        color: #1f77b4 !important;  /* soft blue */
    }
    </style>
""", unsafe_allow_html=True)

# --- Scraper Function ---
@st.cache_data(show_spinner=False)
def get_holdings_from_moneycontrol(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Failed to fetch URL: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 5:
        st.warning("Expected portfolio table not found.")
        return []

    rows = tables[4].find_all("tr")[1:]
    return [row.find_all("td")[0].text.strip() for row in rows if row.find_all("td")]

# --- Comparison Function ---
def compare_funds(fund1, fund2):
    import urllib.parse

    set1 = set(fund1["stocks"])
    set2 = set(fund2["stocks"])
    overlap = set1 & set2
    avg_len = (len(set1) + len(set2)) / 2
    overlap_pct = (len(overlap) / avg_len) * 100

    
    # Diversification score + emoji
    if overlap_pct >= 40:
        score, color, emoji = "Low", "red", "👎"
    elif overlap_pct >= 20:
        score, color, emoji = "Medium", "orange", "⚠️"
    else:
        score, color, emoji = "High", "green", "👍"

    st.markdown("### 📊 Comparison Results")
    st.markdown(f"**Diversification Score:** :{color}[{score} {emoji}]")
    st.markdown(f"**Overlap %:** {overlap_pct:.2f}%")

    st.markdown("**Common Stocks:**")
    if overlap:
        for stock in sorted(overlap):
            st.markdown(f"- {stock}")
    else:
        st.markdown("_None_")

def compare_multiple_funds(fund_names, url_df):
    # 1. Fetch holdings for each fund
    fund_data = []
    for name in fund_names:
        url = url_df[url_df["Fund Name"] == name]["URL"].values[0]
        stocks = get_holdings_from_moneycontrol(url)
        fund_data.append({"name": name, "stocks": stocks})

    # New overlap % logic — "appears in at least one other fund"
    stock_sets = [set(f["stocks"]) for f in fund_data if f["stocks"]]

    if len(stock_sets) < 2:
        st.warning("Could not fetch enough fund data to compare.")
        return

    numerator = 0
    denominator = 0

    for i, fund_set in enumerate(stock_sets):
        denominator += len(fund_set)
        other_sets = stock_sets[:i] + stock_sets[i+1:]
        overlapping_stocks = set()
        for other in other_sets:
            overlapping_stocks.update(fund_set & other)
        numerator += len(overlapping_stocks)

    overlap_pct = (numerator / denominator) * 100 if denominator > 0 else 0

    # 4. Diversification score
    if overlap_pct >= 40:
        score, color, emoji = "Low", "red", "👎"
    elif overlap_pct >= 20:
        score, color, emoji = "Medium", "orange", "⚠️"
    else:
        score, color, emoji = "High", "green", "👍"

    # 5. Show Results
    st.markdown("### 📊 Comparison Results")
    st.markdown(f"**Diversification Score:** :{color}[{score} {emoji}]")
    st.markdown(f"**Overlap %:** {overlap_pct:.2f}%")

   # Social Media Sharing Links
    import urllib.parse

    fund_list_text = " vs ".join(f["name"] for f in fund_data)

    share_text = (
        f"Check out this mutual funds diversification checker:\n\n"
        f"{fund_list_text}\n"
        f"Overlap: {overlap_pct:.2f}%\n"
        f"Diversification Score: {score} {emoji}\n"
        f"Try it here 👉 https://mutual-fund-diversity-score.streamlit.app"
    )

    whatsapp_url = "https://wa.me/?text=" + urllib.parse.quote(share_text)
    linkedin_url = "https://www.linkedin.com/sharing/share-offsite/?url=" + urllib.parse.quote("https://mutual-fund-diversity-score.streamlit.app")

    st.markdown("### 📤 Share This Result")
    st.markdown(
        f"[📲🟢 WhatsApp]({whatsapp_url}) &nbsp;&nbsp;&nbsp; [🔗 LinkedIn]({linkedin_url})",
        unsafe_allow_html=True
    )
    
    # Build a frequency count of stocks across all selected funds
    from collections import Counter

    all_stocks = [stock for s in stock_sets for stock in s]
    stock_freq = Counter(all_stocks)

    # Stocks that appear in 2 or more funds
    common_stocks = [s.strip() for s, count in stock_freq.items() if count > 1 and s.strip()]

    st.markdown("**Common Stocks (across any two or more funds):**")
    if common_stocks:
        for stock in sorted(common_stocks):
            st.write(f"- {stock}")
    else:
        st.markdown("_None_")

# --- Streamlit UI ---

# Ensure session state keys are initialized early
if "num_funds" not in st.session_state:
    st.session_state["num_funds"] = 2
    
if "add_triggered" not in st.session_state:
    st.session_state["add_triggered"] = False

st.title("🔬 Mutual Fund Overlap Checker")
with st.expander("ℹ️ About this tool"):
    st.markdown("""
    Compare up to five mutual funds to see stock overlaps and get a diversification score.
    
    ✅ Live data  
    ✅ Built for Indian investors  
    ✅ Best for reducing over-diversification
    """)

st.markdown("### 🗂 Select Funds to Compare")

df_urls = load_fund_list()
fund_names = df_urls["Fund Name"].tolist()


# Show button only if fewer than 5 funds
cols = st.columns([1, 3])

with cols[0]:
    if st.session_state["num_funds"] < 5:
        if st.button("➕ Add Another Fund"):
            st.session_state["add_triggered"] = True

with cols[1]:
    st.markdown("<span style='font-size: 0.85em; color: gray;'>Add up to 5 funds to compare</span>", unsafe_allow_html=True)

# If triggered, increment count and reset trigger
if st.session_state["add_triggered"]:
    if st.session_state["num_funds"] < 5:
        st.session_state["num_funds"] += 1
    st.session_state["add_triggered"] = False

# Now it's safe to render dropdowns
fund_inputs = []
selected_funds_so_far = []

for i in range(st.session_state["num_funds"]):
    # Filter out already-selected funds from remaining dropdowns
    available_options = [f for f in fund_names if f not in selected_funds_so_far]
    
    fund_input = st.selectbox(
        f"Select Fund {i+1}",
        [""] + available_options,
        key=f"fund_select_{i}"
    )
    
    if fund_input:
        selected_funds_so_far.append(fund_input)
        fund_inputs.append(fund_input)
        

#Compre Button Handling Section    
if st.button("Compare"):
    selected_funds = [f for f in fund_inputs if f]

    if len(selected_funds) < 2:
        st.warning("Please select at least two different mutual funds.")
    else:
        with st.spinner("Fetching live holdings..."):
            compare_multiple_funds(selected_funds, df_urls)
    
        
