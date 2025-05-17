import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# -- Mobile Friendly page layout --
st.set_page_config(
    page_title="Mutual Fund Comparison Tool",
    layout="wide"
)

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
    headers = {"User-Agent": "Mozilla/5.0"}
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
    if overlap_pct >= 50:
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

    # ✅ WhatsApp Share Block
    share_text = (
        f"Check out this mutual fund comparison:\n\n"
        f"{fund1['name']} vs {fund2['name']}\n"
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

def compare_multiple_funds(fund_names, url_df):
    # 1. Fetch holdings for each fund
    fund_data = []
    for name in fund_names:
        url = url_df[url_df["Fund Name"] == name]["URL"].values[0]
        stocks = get_holdings_from_moneycontrol(url)
        fund_data.append({"name": name, "stocks": stocks})

    # 2. Calculate intersection of all stock sets
    all_sets = [set(f["stocks"]) for f in fund_data if f["stocks"]]
    if len(all_sets) < 2:
        st.warning("Could not fetch enough fund data to compare.")
        return

    # New overlap % logic — "appears in at least one other fund"
stock_sets = [set(f["stocks"]) for f in fund_data if f["stocks"]]

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
    if overlap_pct >= 50:
        score, color, emoji = "Low", "red", "👎"
    elif overlap_pct >= 20:
        score, color, emoji = "Medium", "orange", "⚠️"
    else:
        score, color, emoji = "High", "green", "👍"

    # 5. Show Results
    st.markdown("### 📊 Comparison Results")
    st.markdown(f"**Diversification Score:** :{color}[{score} {emoji}]")
    st.markdown(f"**Overlap %:** {overlap_pct:.2f}%")

    st.markdown("**Common Stocks:**")
    if common_stocks:
        for stock in sorted(common_stocks):
            st.markdown(f"- {stock}")
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
    Compare two mutual funds to see stock overlaps and get a diversification score.
    
    ✅ Live data  
    ✅ Built for Indian investors  
    ✅ Best for reducing over-diversification
    """)

st.markdown("### 🗂 Select Funds to Compare")

df_urls = load_fund_list()
fund_names = df_urls["Fund Name"].tolist()


# Show button only if fewer than 5 funds
if st.session_state["num_funds"] < 5:
    if st.button("➕ Add Another Fund"):
        st.session_state["add_triggered"] = True

# If triggered, increment count and reset trigger
if st.session_state["add_triggered"]:
    if st.session_state["num_funds"] < 5:
        st.session_state["num_funds"] += 1
    st.session_state["add_triggered"] = False

# Now it's safe to render dropdowns
fund_inputs = []
for i in range(st.session_state["num_funds"]):
    fund_input = st.selectbox(
        f"Select Fund {i+1}",
        [""] + fund_names,
        key=f"fund_select_{i}"
    )
    if fund_input:
        fund_inputs.append(fund_input)
        

#Compre Button Handling Section    
if st.button("Compare"):
    selected_funds = [f for f in fund_inputs if f]

    if len(selected_funds) < 2:
        st.warning("Please select at least two different mutual funds.")
    else:
        with st.spinner("Fetching live holdings..."):
            compare_multiple_funds(selected_funds, df_urls)
    
        
