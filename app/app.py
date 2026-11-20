from pathlib import Path

import branca.colormap as cm
import folium
import geopandas as gpd
import streamlit as st
from folium.plugins import BeautifyIcon
from streamlit_folium import st_folium

st.set_page_config(page_title="Toronto Bubble Tea Site Selection", layout="wide")
DATA = Path(__file__).parent / "data"

# Area names for the recommended sites (checked in Google Maps)
AREAS = {
    1: "St. James Town",
    2: "St. Clair West (Oakwood)",
    3: "Sheppard East (near Fairview Mall)",
    4: "Eglinton West (Little Jamaica)",
    5: "Queen West (Parkdale / Roncesvalles)",
}


@st.cache_data
def load_data():
    hexes = gpd.read_file(DATA / "hexes.geojson")
    shops = gpd.read_file(DATA / "bubble_tea.geojson")
    top5 = gpd.read_file(DATA / "top5.geojson").sort_values("final_rank")
    top5["area"] = top5["final_rank"].astype(int).map(AREAS)
    lines = gpd.read_file(DATA / "transit_lines.geojson")
    stations = gpd.read_file(DATA / "stations.geojson")
    return hexes, shops, top5, lines, stations


hexes, shops, top5, lines, stations = load_data()
smax = float(hexes["suitability"].max())

# ---------- Sidebar ----------
with st.sidebar:
    st.header("About this project")
    st.write(
        "A geospatial model that scores every part of Toronto on how suitable it is "
        "for a bubble tea shop, then recommends five locations after accounting for "
        "competition and a field check."
    )
    st.metric("Spatial CV ROC AUC", "0.894")
    st.caption(
        "The model ranks an area with a shop above one without 89% of the time, "
        "tested on parts of the city it never trained on. This measures ranking "
        "ability, not accuracy or profitability."
    )
    st.metric("Areas scored", f"{len(hexes):,} hexagons")
    st.metric("Existing shops mapped", f"{len(shops)}")
    st.markdown(
        "**Strongest signals:** food & drink places nearby, share of young adults, "
        "and lower-to-middle household income.\n\n"
        "**Data:** Statistics Canada 2021 Census, TTC GTFS, StatCan educational "
        "facilities, OpenStreetMap."
    )
    st.warning(
        "**Suitability, not profitability.** The model learns where bubble tea shops "
        "already exist (94 of 846 areas), not which ones succeed. Rent, sales, and "
        "competitor quality aren't included. Treat results as a shortlist for "
        "further study."
    )
    st.markdown(
        "[View the code on GitHub](https://github.com/shaheryar-haider/retail-site-selection)"
    )

# ---------- Header ----------
st.title("Where should the next bubble tea shop open in Toronto?")
st.caption("Darker hexagons are more suitable. Hover over a hexagon for details; "
           "click a numbered marker to see its field-check notes. Markers sit at "
           "each area's commercial center, where its shops and restaurants cluster, "
           "rather than the middle of the hexagon.")

# ---------- Map ----------
m = folium.Map(location=[43.70, -79.40], zoom_start=11, tiles=None)
folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)

# Remove the browser focus outline that appears after clicking a hexagon
m.get_root().header.add_child(
    folium.Element("<style>.leaflet-interactive:focus { outline: none; }</style>"))

cmap = cm.LinearColormap(["#ffffcc", "#41b6c4", "#081d58"], vmin=0, vmax=smax,
                         caption="Suitability score")


def hex_style(feature):
    s = feature["properties"]["suitability"]
    return {
        "fillColor": cmap(s),
        "color": "none",
        # Fade out low scores so strong areas stand out
        "fillOpacity": 0 if s < 0.05 else 0.25 + 0.5 * s / smax,
    }


folium.GeoJson(
    hexes,
    name="Suitability",
    style_function=hex_style,
    tooltip=folium.GeoJsonTooltip(
        fields=["suitability", "catchment_15_34", "food_places_500m",
                "competitors_1km", "median_hh_income"],
        aliases=["Suitability", "Residents 15–34 nearby", "Food places within 500 m",
                 "Competitors within 1 km", "Median household income ($)"],
    ),
).add_to(m)
cmap.add_to(m)

# Transit lines and stations (current service only, matching the model)
transit_layer = folium.FeatureGroup(name="Subway & LRT")
for _, ln in lines.iterrows():
    folium.PolyLine(
        [(lat, lon) for lon, lat in ln.geometry.coords],
        color=ln["color"], weight=4, opacity=0.85, tooltip=ln["name"],
    ).add_to(transit_layer)
for _, st_ in stations.iterrows():
    folium.CircleMarker(
        [st_.geometry.y, st_.geometry.x], radius=3, color="#333333", weight=1,
        fill=True, fill_color="white", fill_opacity=1, tooltip=st_["name"],
    ).add_to(transit_layer)
transit_layer.add_to(m)

# Existing shops
shop_layer = folium.FeatureGroup(name="Existing bubble tea shops")
for _, s in shops.iterrows():
    folium.CircleMarker(
        [s.geometry.y, s.geometry.x], radius=2.5, color="red", weight=0,
        fill=True, fill_opacity=0.8, tooltip=s["name"],
    ).add_to(shop_layer)
shop_layer.add_to(m)

# Recommended sites
site_layer = folium.FeatureGroup(name="Recommended sites")
for _, r in top5.iterrows():
    rank = int(r["final_rank"])
    folium.Marker(
        [r["lat"], r["lon"]],
        tooltip=f"#{rank} {r['area']}",
        popup=folium.Popup(f"<b>#{rank} {r['area']}</b><br>{r['notes']}", max_width=250),
        icon=BeautifyIcon(number=rank, icon_shape="marker", background_color="#f39c12",
                          border_color="#7a4a00", text_color="white"),
    ).add_to(site_layer)
site_layer.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)
st_folium(m, height=650, use_container_width=True, returned_objects=[])

# ---------- Table ----------
st.subheader("Top 5 recommended sites")
table = top5[["final_rank", "area", "opportunity", "catchment_15_34", "food_in_hex",
              "median_hh_income", "notes"]].rename(columns={
    "final_rank": "Rank", "area": "Area", "opportunity": "Opportunity score",
    "catchment_15_34": "Residents 15–34 nearby", "food_in_hex": "Food places",
    "median_hh_income": "Median income ($)", "notes": "Field check notes"})
st.dataframe(table, hide_index=True, use_container_width=True)

st.caption("Opportunity = suitability × 1 / (1 + competitors within 1 km). Sites must "
           "have at least the city-median number of young residents nearby and 3+ "
           "food places, and were reviewed in Google Maps before selection.")