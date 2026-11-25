"""«Inson» markazlari: kim xizmatdan uzoqda qolmoqda? — Streamlit ilovasi.

Ilova hisob-kitob qilmaydi: Colab'da tayyorlangan natijani (data/ilova_data.gpkg) koʻrsatadi.
"""
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from folium import GeoJson, GeoJsonTooltip, LayerControl
from streamlit_folium import st_folium

st.set_page_config(page_title="«Inson» markazlari — kim uzoqda qolmoqda?", layout="wide")

DATA = Path(__file__).parent / "data" / "ilova_data.gpkg"

# Foiz sinflari va ketma-ket palitra (OrRd — qizil–yashil emas)
CHEGARA = [10, 30, 60, 85]
RANGLAR = ["#FEF0D9", "#FDCC8A", "#FC8D59", "#E34A33", "#B30000"]
NOMLAR = ["0–10 %", "10–30 %", "30–60 %", "60–85 %", "85–100 %"]


@st.cache_data
def yukla():
    """Maʼlumotni bir marta oʻqiydi."""
    natija = gpd.read_file(DATA, layer="natija")
    obyektlar = gpd.read_file(DATA, layer="obyektlar")
    return natija, obyektlar


def sinf(p):
    for i, b in enumerate(CHEGARA):
        if p < b:
            return i
    return len(CHEGARA)


def son(x):
    return f"{x:,.0f}".replace(",", " ")


natija, obyektlar = yukla()

# ---------- Chap panel ----------
st.sidebar.header("Filtr")
hududlar = ["Ikkalasi"] + sorted(natija["hudud"].dropna().unique().tolist())
hudud = st.sidebar.selectbox("Hudud", hududlar)
R = st.sidebar.slider("Masofa chegarasi (km)", min_value=1, max_value=10, value=5, step=1,
                      help="«Inson» markazidan shu masofadan uzoqda yashovchi aholi hisoblanadi.")
st.sidebar.caption("Masofa «Inson» markazigacha toʻgʻri chiziqda hisoblangan.")

df = natija if hudud == "Ikkalasi" else natija[natija["hudud"] == hudud]
ob = obyektlar if hudud == "Ikkalasi" else obyektlar[obyektlar["hudud"] == hudud]

uzoq_a, uzoq_p = f"uzoq{R}_aholi", f"uzoq{R}_pct"

# ---------- Sarlavha va raqamlar ----------
st.title("«Inson» markazlaridan kim uzoqda qolmoqda?")
st.caption("Toshkent shahri va viloyati: markazdan tanlangan masofadan (1–10 km) uzoqda yashovchi aholi")

jami = df["aholi"].sum()
uzoq = df[uzoq_a].sum()
c1, c2, c3 = st.columns(3)
c1.metric("«Inson» markazlari soni", int(df["markazlar"].sum()))
c2.metric(f"{R} km dan uzoqdagi aholi", son(uzoq))
c3.metric("Aholining ulushi", f"{(100 * uzoq / jami if jami else 0):.1f} %".replace(".", ","))

# ---------- Xarita ----------
g = df[["nomi", "hudud", "aholi", "markazlar", uzoq_a, uzoq_p, "geometry"]].copy()
g["rang"] = g[uzoq_p].apply(lambda p: RANGLAR[sinf(p)])
g["aholi_s"] = g["aholi"].apply(son)
g["uzoq_s"] = g[uzoq_a].apply(son)
g["ulush_s"] = g[uzoq_p].round(1).astype(str).str.replace(".", ",", regex=False) + " %"
g["mk"] = g["markazlar"].astype(int)
g = g[["nomi", "aholi_s", "mk", "uzoq_s", "ulush_s", "rang", "geometry"]]

xmin, ymin, xmax, ymax = df.total_bounds
m = folium.Map(tiles="OpenStreetMap")
m.fit_bounds([[ymin, xmin], [ymax, xmax]])

GeoJson(
    g,
    name=f"{R} km dan uzoqdagi aholi ulushi (%)",
    style_function=lambda f: {"fillColor": f["properties"]["rang"], "color": "#FFFFFF", "weight": 0.8, "fillOpacity": 0.8},
    highlight_function=lambda f: {"weight": 3, "color": "#000000"},
    tooltip=GeoJsonTooltip(
        fields=["nomi", "aholi_s", "mk", "uzoq_s", "ulush_s"],
        aliases=["Tuman:", "Aholi:", "«Inson» markazlari:", f"{R} km dan uzoqda (kishi):", f"{R} km dan uzoqda (%):"],
        sticky=True,
    ),
).add_to(m)

fg = folium.FeatureGroup(name="«Inson» markazlari")
for _, row in ob.iterrows():
    folium.CircleMarker(
        [row.geometry.y, row.geometry.x], radius=5, color="#08306b", weight=1,
        fill=True, fill_color="#2171b5", fill_opacity=1, tooltip=str(row["name"]),
    ).add_to(fg)
fg.add_to(m)

satrlar = "".join(
    f'<div><span style="background:{c};width:14px;height:14px;display:inline-block;margin-right:6px;border:1px solid #777"></span>{n}</div>'
    for c, n in zip(RANGLAR, NOMLAR)
)
m.get_root().html.add_child(folium.Element(
    f'<div style="position:fixed;bottom:25px;left:25px;z-index:9999;background:white;padding:8px 10px;'
    f'border:1px solid #888;border-radius:6px;font:12px Arial;line-height:1.5">'
    f"<b>{R} km dan uzoqda yashovchi<br>aholi ulushi</b>{satrlar}</div>"
))
LayerControl(collapsed=False).add_to(m)

col_xarita, col_jadval = st.columns([3, 2])
with col_xarita:
    st_folium(m, height=560, use_container_width=True, returned_objects=[])

# ---------- Eng ogʻir 10 ta tuman ----------
with col_jadval:
    st.subheader(f"Eng ogʻir 10 ta tuman ({R} km)")
    top = df.nlargest(10, uzoq_a)[["nomi", "hudud", "markazlar", uzoq_a, uzoq_p]].copy()
    top[uzoq_a] = top[uzoq_a].round(0).astype(int)
    top[uzoq_p] = top[uzoq_p].round(1)
    top.columns = ["Tuman", "Hudud", "Markazlar soni", "Uzoqdagi aholi (kishi)", "Ulushi (%)"]
    st.dataframe(top, hide_index=True, width="stretch")
    st.caption("Tartib: uzoqda yashovchi aholining soni boʻyicha.")

# ---------- Masofa egri chizigʻi ----------
st.subheader("Masofa kengaygan sari uzoqda qolganlar qanday kamayadi?")
egri = pd.DataFrame({
    "Masofa (km)": list(range(1, 11)),
    "Uzoqdagi aholi ulushi (%)": [round(100 * df[f"uzoq{k}_aholi"].sum() / jami, 1) if jami else 0 for k in range(1, 11)],
    "Uzoqdagi aholi (kishi)": [int(df[f"uzoq{k}_aholi"].sum()) for k in range(1, 11)],
})
e1, e2 = st.columns([3, 2])
with e1:
    st.line_chart(egri, x="Masofa (km)", y="Uzoqdagi aholi ulushi (%)", height=300)
with e2:
    ko = egri.copy()
    ko["Uzoqdagi aholi (kishi)"] = ko["Uzoqdagi aholi (kishi)"].apply(son)
    st.dataframe(ko, hide_index=True, width="stretch", height=300)
st.caption("Egri chiziq tanlangan hudud (chap panel) uchun; slayder faqat xarita va raqamlarni oʻzgartiradi.")

# ---------- Manba va cheklovlar ----------
st.markdown("---")
st.markdown(
    "**Manba:** loyiha_toplami.gpkg (tuman chegaralari, «Inson» markazlari), aholi rastri 100 m, stat.uz.  \n"
    "**Cheklovlar:** (1) masofa toʻgʻri chiziqda — yoʻl va transport hisobga olinmagan; "
    "(2) aholi rastri barcha yoshni qamrab oladi, markazlarning sigʻimi hisobga olinmagan; "
    "(3) bufer EPSG:32642 da qurilgan, xaritadagi chegaralar soddalashtirilgan."
)
