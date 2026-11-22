from pathlib import Path

import branca.colormap as cm
import folium
import geopandas as gpd
import streamlit as st
from folium.plugins import BeautifyIcon
from streamlit_folium import st_folium

st.set_page_config(page_title="Toronto Bubble Tea Site Selection", page_icon="🧋",
                   layout="wide")
DATA = Path(__file__).parent / "data"
FIGURES = Path(__file__).parent.parent / "figures"

# ---------- Palette: bubble tea flavours ----------
PEARL = "#2B1D16"         # tapioca pearls = existing shops, and body text
TARO = "#6B4C9A"          # taro = suitability
TARO_LIGHT = "#B9A3D9"
TARO_RAMP = ["#EDE4F5", "#B9A3D9", "#7B5EA7", "#3E2A5E"]  # pale taro -> deep taro
MANGO = "#F08A24"         # mango = recommended sites
MANGO_DARK = "#9A4A0B"

AREAS = {
    1: "St. James Town",
    2: "St. Clair West (Oakwood)",
    3: "Sheppard East (near Fairview Mall)",
    4: "Eglinton West (Little Jamaica)",
    5: "Queen West (Parkdale / Roncesvalles)",
}
REASONS = {
    1: "Dense high-rise neighbourhood with daily-needs retail and no bubble tea within 1 km.",
    2: "Busy commercial strip with restaurants, banks, and shops.",
    3: "Strong food cluster in North York, near Fairview Mall.",
    4: "On the new Line 5 Eglinton, so foot traffic should keep growing.",
    5: "High foot traffic, with higher-income residents nearby.",
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700&family=Figtree:wght@400;500;600&display=swap');

.stApp p, .stApp li {{ font-family: 'Figtree', sans-serif; }}
h2, h3 {{ font-family: 'Bricolage Grotesque', sans-serif !important; letter-spacing: -0.02em; }}
.block-container {{ padding-top: 2.5rem; max-width: 1300px; }}

/* Hide the automatic link icon Streamlit adds next to headings */
[data-testid="stHeaderActionElements"], .hero a {{ display: none !important; }}

.hero h1 {{
    font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
    font-size: clamp(2.2rem, 4vw, 3.4rem); line-height: 1.04; letter-spacing: -0.03em;
    color: {PEARL}; margin: 0 0 0.8rem; max-width: 16ch; padding: 0;
    text-wrap: balance;
}}
.hero p {{ font-size: 1.1rem; max-width: 58ch; color: #5A4A42; margin: 0 0 1.5rem; }}

.stApp .side-title {{ font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.35rem;
                      font-weight: 700; letter-spacing: -0.02em; margin: 0 0 1rem; color: {PEARL}; }}

.finding {{ border-left: 3px solid {TARO_LIGHT}; padding: 0.2rem 0 0.2rem 0.8rem;
            margin-bottom: 0.9rem; font-size: 0.95rem; color: #3D2E27; }}
.finding b {{ color: {PEARL}; }}

.site {{
    background: #FFFFFF; border-left: 4px solid {MANGO}; border-radius: 6px;
    padding: 0.9rem 1rem; margin-bottom: 0.75rem;
}}
.site-head {{ display: flex; align-items: baseline; gap: 0.6rem; }}
.site-rank {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
              font-size: 1.6rem; color: {MANGO}; }}
.site-name {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
              font-size: 1.05rem; color: {PEARL}; }}
.site-why {{ margin: 0.35rem 0 0.5rem; font-size: 0.93rem; color: #3D2E27; }}
.site-stats {{ display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; font-size: 0.82rem; color: #6E5A50; }}
.site-stats b {{ color: {PEARL}; }}

.legend {{ display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem;
           font-size: 0.85rem; color: #5A4A42; margin-top: 0.4rem; }}
.legend .bar {{ width: 140px; height: 10px; border-radius: 5px;
                background: linear-gradient(90deg, {", ".join(TARO_RAMP)}); }}
.legend .dot {{ width: 11px; height: 11px; border-radius: 50%; margin-left: 1rem; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    hexes = gpd.read_file(DATA / "hexes.geojson")
    shops = gpd.read_file(DATA / "bubble_tea.geojson")
    top5 = gpd.read_file(DATA / "top5.geojson").sort_values("final_rank")
    top5["rank"] = top5["final_rank"].astype(int)
    top5["area"] = top5["rank"].map(AREAS)
    lines = gpd.read_file(DATA / "transit_lines.geojson")
    stations = gpd.read_file(DATA / "stations.geojson")
    return hexes, shops, top5, lines, stations


hexes, shops, top5, lines, stations = load_data()
smax = float(hexes["suitability"].max())

# ---------- Hero ----------
hero_left, hero_right = st.columns([1.6, 1], gap="large")

with hero_left:
    st.markdown("""
    <div class="hero">
      <h1>Where does Toronto have the crowds but not the bubble tea?</h1>
      <p>A location model scored 846 areas of the city on young residents, street
      activity, transit, and income, then picked five spots with strong demand and
      few or no shops nearby.</p>
    </div>
    """, unsafe_allow_html=True)

with hero_right:
    st.markdown("""
    <p class="side-title">What the model found</p>
    <div class="finding"><b>Street activity matters most.</b> Areas with a bubble tea
    shop have a median of 26 food places within 500 m, compared with 1 elsewhere.</div>
    <div class="finding"><b>Busy beats wealthy.</b> Higher-income areas score lower:
    the odds drop about 30% with each step up in neighbourhood income.</div>
    <div class="finding"><b>Young neighbourhoods help.</b> Areas with a shop have
    1.6× more residents aged 15–34 within about 1 km.</div>
    """, unsafe_allow_html=True)

# ---------- Map ----------
m = folium.Map(location=[43.715, -79.385], zoom_start=11, scrollWheelZoom=False, tiles=None)
folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
m.get_root().header.add_child(folium.Element(
    "<style>.leaflet-interactive:focus { outline: none; }</style>"))

cmap = cm.LinearColormap(TARO_RAMP, vmin=0, vmax=smax)


def hex_style(feature):
    s = feature["properties"]["suitability"]
    return {
        "fillColor": cmap(s),
        "color": "white",
        "weight": 0.4,
        "fillOpacity": 0.06 + 0.74 * s / smax,
    }


folium.GeoJson(
    hexes, name="Suitability", style_function=hex_style,
    tooltip=folium.GeoJsonTooltip(
        fields=["suitability", "catchment_15_34", "food_places_500m",
                "competitors_1km", "median_hh_income"],
        aliases=["Suitability", "Residents 15–34 nearby", "Food places within 500 m",
                 "Competitors within 1 km", "Median household income ($)"],
    ),
).add_to(m)

transit_layer = folium.FeatureGroup(name="Subway & LRT")
for _, ln in lines.iterrows():
    folium.PolyLine([(lat, lon) for lon, lat in ln.geometry.coords],
                    color=ln["color"], weight=3.5, opacity=0.85,
                    tooltip=ln["name"]).add_to(transit_layer)
for _, st_ in stations.iterrows():
    folium.CircleMarker([st_.geometry.y, st_.geometry.x], radius=2.5, color="#555555",
                        weight=1, fill=True, fill_color="white", fill_opacity=1,
                        tooltip=st_["name"]).add_to(transit_layer)
transit_layer.add_to(m)

shop_layer = folium.FeatureGroup(name="Existing bubble tea shops")
for _, s in shops.iterrows():
    folium.CircleMarker([s.geometry.y, s.geometry.x], radius=3.5, color="white", weight=1,
                        fill=True, fill_color=PEARL, fill_opacity=0.95,
                        tooltip=s["name"]).add_to(shop_layer)
shop_layer.add_to(m)

site_layer = folium.FeatureGroup(name="Recommended sites")
for _, r in top5.iterrows():
    folium.Marker(
        [r["lat"], r["lon"]],
        tooltip=f"#{r['rank']} {r['area']}",
        popup=folium.Popup(f"<b>#{r['rank']} {r['area']}</b><br>{REASONS[r['rank']]}",
                           max_width=250),
        icon=BeautifyIcon(number=r["rank"], icon_shape="marker", background_color=MANGO,
                          border_color=MANGO_DARK, text_color="white"),
    ).add_to(site_layer)
site_layer.add_to(m)

folium.LayerControl(collapsed=True).add_to(m)

col_map, col_sites = st.columns([2.2, 1], gap="large")

with col_map:
    st_folium(m, height=680, use_container_width=True, returned_objects=[])
    st.markdown(f"""
    <div class="legend">
      <span>Less suitable</span><div class="bar"></div><span>More suitable</span>
      <div class="dot" style="background:{PEARL}"></div><span>Existing shop</span>
      <div class="dot" style="background:{MANGO}"></div><span>Recommended site</span>
    </div>""", unsafe_allow_html=True)

with col_sites:
    st.markdown('<p class="side-title">Five recommended sites</p>', unsafe_allow_html=True)
    cards = ""
    for _, r in top5.iterrows():
        cards += f"""
        <div class="site">
          <div class="site-head">
            <span class="site-rank">{r['rank']}</span>
            <span class="site-name">{r['area']}</span>
          </div>
          <p class="site-why">{REASONS[r['rank']]}</p>
          <div class="site-stats">
            <span><b>{r['catchment_15_34'] / 1000:.0f}k</b> residents aged 15–34 nearby</span>
            <span><b>{int(r['food_in_hex'])}</b> food places</span>
          </div>
        </div>"""
    st.markdown(cards, unsafe_allow_html=True)

# ---------- How it works ----------
st.subheader("How the sites were chosen")
c1, c2, c3 = st.columns(3, gap="large")
with c1:
    st.markdown(
        "**1. Score every area**\n\n"
        "A logistic regression scored 846 hexagons on young residents nearby, street "
        "activity, transit access, and income. Tested on parts of the city it never "
        "saw, it ranks an area with a shop above one without 89% of the time "
        "(ROC AUC 0.894).")
with c2:
    st.markdown(
        "**2. Factor in competition**\n\n"
        "Opportunity = suitability × 1 / (1 + shops within 1 km). Each site also "
        "needed at least the city-median number of young residents nearby and an "
        "active commercial street.")
with c3:
    st.markdown(
        "**3. Check on the ground**\n\n"
        "The top 10 were reviewed in Google Maps and Street View, and five were kept. "
        "Each marker sits at its area's commercial center, where shops cluster.")

# ---------- Under the hood ----------
st.subheader("Under the hood")
t1, t2, t3 = st.tabs(["Model comparison", "What drives the score", "Testing on unseen areas"])
with t1:
    st.image(str(FIGURES / "model_comparison.png"), width=700)
    st.caption("Five models were tested on the same spatial folds. The simplest, "
               "logistic regression, scored best: with only 94 areas that have a "
               "shop, more flexible models overfit.")
with t2:
    st.image(str(FIGURES / "logit_coefficients.png"), width=700)
    st.caption("Blue raises suitability, red lowers it. Food & drink places nearby "
               "dominate; higher income lowers the score.")
with t3:
    st.image(str(FIGURES / "cv_comparison.png"), width=550)
    st.caption("Neighbouring areas look alike, so a random train/test split can "
               "overstate accuracy. Holding out whole blocks of the city gave "
               "almost the same score, so the model generalizes to new areas.")

st.warning(
    "**Suitability, not profitability.** The model learns where bubble tea shops already "
    "exist (94 of 846 areas), not which ones succeed. Rent, sales, and competitor quality "
    "aren't included, so treat these as a shortlist for further study.")

st.caption(
    "Data: Statistics Canada 2021 Census, TTC GTFS, StatCan Open Database of Educational "
    "Facilities, OpenStreetMap contributors. "
    "[Code on GitHub](https://github.com/shaheryar-haider/retail-site-selection)")