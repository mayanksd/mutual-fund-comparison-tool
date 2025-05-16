import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup



# --- Scraper Function ---
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
    set1 = set(fund1["stocks"])
    set2 = set(fund2["stocks"])
    overlap = set1 & set2
    avg_len = (len(set1) + len(set2)) / 2
    overlap_pct = (len(overlap) / avg_len) * 100

    # Diversification score
    if overlap_pct >= 50:
        score, color = "Low", "red"
    elif overlap_pct >= 20:
        score, color = "Medium", "orange"
    else:
        score, color = "High", "green"

    st.subheader("📊 Results")
    st.markdown(f"**Diversification Score:** :{color}[{score}]")
    st.markdown(f"**Overlap %:** {overlap_pct:.2f}%")

    st.markdown("**Common Stocks:**")
    if overlap:
        for stock in sorted(overlap):
            st.markdown(f"- {stock}")
    else:
        st.markdown("_None_")

# --- Load fund list ---
@st.cache_data
def load_fund_list():
    df = pd.read_excel("fund_urls.xlsx")
    df = df.dropna(subset=["Fund Name", "URL"])
    df["Fund Name"] = df["Fund Name"].str.strip()
    df["URL"] = df["URL"].str.strip()
    return df

# --- Streamlit UI ---
st.title("🧮 Mutual Fund Overlap Checker")

df_urls = load_fund_list()
fund_names = df_urls["Fund Name"].tolist()

#old UI of plaindropdown fund1_name = st.selectbox("Select First Fund", fund_names)
fund1_name = st.selectbox(
    "First Fund (Please Start typing...)",
    [""] + fund_names,
    index=0
)

#old UI of plaindropdown  fund2_name = st.selectbox("Select Second Fund", fund_names, index=1)

fund2_name = st.selectbox(
    "Second Fund (Please Start typing...)",
    [""] + fund_names,
    index=0
)

if st.button("Compare"):
    url1 = df_urls[df_urls["Fund Name"] == fund1_name]["URL"].values[0]
    url2 = df_urls[df_urls["Fund Name"] == fund2_name]["URL"].values[0]

    with st.spinner("Fetching live holdings..."):
        fund1 = {"name": fund1_name, "stocks": get_holdings_from_moneycontrol(url1)}
        fund2 = {"name": fund2_name, "stocks": get_holdings_from_moneycontrol(url2)}

    compare_funds(fund1, fund2)
