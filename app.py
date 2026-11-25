"""
«Inson» markazlaridan kim uzoqda qolmoqda? — Streamlit ilovasi.

Ishga tushirish:   streamlit run app.py
Ma’lumot fayli:    data/ilova_data.gpkg  (bu app.py yonidagi "data" papkada turishi kerak)
"""
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import streamlit as st
from streamlit_folium import st_folium

# ------------------------------------------------------------------
# 1. Umumiy sozlamalar
# ------------------------------------------------------------------
st.set_page_config(page_title="«Inson» markazlari", layout="wide")

# Xarita sinflari: 0–10 / 10–25 / 25–50 / 50–75 / 75–100 %
CHEGARALAR = [10, 25, 50, 75]
# YlOrRd palitrasi (och sariqdan to to‘q qizilgacha, qizil–yashil emas)
RANGLAR = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
NOMLAR = ["0–10 %", "10–25 %", "25–50 %", "50–75 %", "75–100 %"]


def son_yoz(x):
    """Sonni o‘qish oson ko‘rinishda yozadi: 1234567 -> '1 234 567'."""
    return f"{int(round(x)):,}".replace(",", " ")


def birlashtir(geoseriya):
    """Bir nechta geometriyani bittaga birlashtiradi (geopandas versiyasiga moslab)."""
    if hasattr(geoseriya, "union_all"):
        return geoseriya.union_all()
    return geoseriya.unary_union


# ------------------------------------------------------------------
# 2. Ma’lumotni bir marta yuklash (keshlanadi)
# ------------------------------------------------------------------
@st.cache_data
def yukla():
    fayl = Path(__file__).parent / "data" / "ilova_data.gpkg"
    natija = gpd.read_file(fayl, layer="natija")
    obyektlar = gpd.read_file(fayl, layer="obyektlar")
    return natija, obyektlar


natija, obyektlar = yukla()

# ------------------------------------------------------------------
# 3. Sarlavha va chap panel
# ------------------------------------------------------------------
st.title("«Inson» markazlaridan kim uzoqda qolmoqda?")
st.caption("Tanlangan masofadan tashqarida, ya’ni «Inson» markazidan uzoqda yashaydigan aholi.")

st.sidebar.header("Tanlov")
hudud = st.sidebar.radio("Hudud", ["Ikkalasi", "Toshkent shahri", "Toshkent viloyati"])
masofa = st.sidebar.radio("Masofa chegarasi", ["3 km", "5 km"], index=1, horizontal=True)
km = 3 if masofa == "3 km" else 5

# Tanlangan masofaga mos ustun nomlari
kol_aholi = f"uzoq{km}_aholi"
kol_pct = f"uzoq{km}_pct"

# ------------------------------------------------------------------
# 4. Hudud bo‘yicha saralash
# ------------------------------------------------------------------
if hudud == "Ikkalasi":
    f = natija.copy()
    nuqtalar = obyektlar.copy()
else:
    f = natija[natija["hudud"] == hudud].copy()
    # Faqat tanlangan hudud ichidagi markazlarni qoldiramiz
    nuqtalar = obyektlar[obyektlar.intersects(birlashtir(f.geometry))].copy()

if f.empty:
    st.warning("Tanlangan hudud uchun ma’lumot topilmadi.")
    st.stop()

# ------------------------------------------------------------------
# 5. Uchta asosiy raqam
# ------------------------------------------------------------------
markazlar_soni = int(f["markazlar"].sum())
uzoq_aholi = float(f[kol_aholi].sum())
jami_aholi = float(f["aholi"].sum())
ulush = uzoq_aholi / jami_aholi * 100 if jami_aholi > 0 else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("«Inson» markazlari soni", son_yoz(markazlar_soni))
c2.metric(f"Uzoqdagi aholi ({km} km dan tashqarida)", son_yoz(uzoq_aholi))
c3.metric("Uzoqdagi aholi ulushi", f"{ulush:.1f} %")

# ------------------------------------------------------------------
# 6. Xarita uchun ma’lumotni tayyorlash
# ------------------------------------------------------------------
xar = f[["nomi", "geometry"]].copy()
xar["pct"] = f[kol_pct].fillna(0).round(2)
xar["markaz_s"] = f["markazlar"].astype(int).astype(str)
xar["aholi_s"] = f["aholi"].map(son_yoz)
xar["uzoq_s"] = f[kol_aholi].map(son_yoz) + " (" + f[kol_pct].map(lambda v: f"{v:.1f}") + " %)"

# Har bir sinfda nechta tuman borligi (legenda uchun)
sinf_soni = np.bincount(np.digitize(xar["pct"], CHEGARALAR), minlength=5)


def rang_ber(p):
    """Foizga qarab rang tanlaydi."""
    return RANGLAR[int(np.digitize(p, CHEGARALAR))]


# ------------------------------------------------------------------
# 7. Xaritani qurish
# ------------------------------------------------------------------
minx, miny, maxx, maxy = xar.total_bounds
xarita = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], tiles=None, control_scale=True)
xarita.fit_bounds([[miny, minx], [maxy, maxx]])

# Fon: OpenStreetMap (zaxira sifatida Esri ham bor — panelda almashtiriladi)
folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(xarita)
folium.TileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    name="Esri ko‘cha xaritasi (zaxira)", attr="Tiles © Esri", max_zoom=18,
).add_to(xarita)

# Xoroplet: tumanlar uzoqdagi aholi ulushiga qarab bo‘yaladi
folium.GeoJson(
    xar,
    name=f"Uzoqdagi aholi ulushi ({km} km)",
    style_function=lambda x: {
        "fillColor": rang_ber(x["properties"]["pct"]),
        "color": "#ffffff", "weight": 0.8, "fillOpacity": 0.8,
    },
    highlight_function=lambda x: {"weight": 2.5, "color": "#000000", "fillOpacity": 0.9},
    tooltip=folium.GeoJsonTooltip(
        fields=["nomi", "markaz_s", "aholi_s", "uzoq_s"],
        aliases=["Tuman:", "«Inson» markazlari:", "Aholi:", f"{km} km dan tashqarida:"],
        sticky=True, localize=False,
    ),
).add_to(xarita)

# «Inson» markazlari — alohida qatlam (panelda yoqiladi/o‘chiriladi)
markaz_qatlami = folium.FeatureGroup(name="«Inson» markazlari", show=True)
for _, q in nuqtalar.iterrows():
    folium.CircleMarker(
        location=[q.geometry.y, q.geometry.x], radius=5,
        color="#ffffff", weight=1, fill=True, fill_color="#08519c", fill_opacity=0.95,
        tooltip=str(q["name"]),
    ).add_to(markaz_qatlami)
markaz_qatlami.add_to(xarita)

folium.LayerControl(collapsed=False).add_to(xarita)

# O‘zbekcha legenda (har sinfda tumanlar soni bilan)
qatorlar = "".join(
    f'<div style="margin:2px 0"><span style="display:inline-block;width:18px;height:12px;'
    f'background:{rang};border:1px solid #999;margin-right:6px"></span>{nom} — <b>{int(n)}</b> ta tuman</div>'
    for rang, nom, n in zip(RANGLAR, NOMLAR, sinf_soni)
)
legenda = f"""
<div style="position:fixed;bottom:30px;right:10px;z-index:9999;background:white;padding:10px 12px;
 border:1px solid #999;border-radius:6px;font:13px Arial,sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)">
 <b>{km} km dan tashqaridagi<br>aholi ulushi (%)</b>
 <div style="margin-top:6px">{qatorlar}</div>
 <div style="margin-top:8px"><span style="display:inline-block;width:12px;height:12px;border-radius:50%;
 background:#08519c;border:1px solid #fff;margin-right:6px;box-shadow:0 0 0 1px #777"></span>«Inson» markazi</div>
</div>"""
xarita.get_root().html.add_child(folium.Element(legenda))

# ------------------------------------------------------------------
# 8. Xarita (chapda) va eng og‘ir 10 tuman jadvali (o‘ngda)
# ------------------------------------------------------------------
chap, ong = st.columns([3, 2])

with chap:
    # returned_objects=[] — xaritani bosganda ilova qayta ishlamaydi, shuning uchun tez ishlaydi
    st_folium(xarita, height=600, use_container_width=True, returned_objects=[])

with ong:
    st.subheader("Eng og‘ir 10 ta tuman")
    st.caption(f"Uzoqdagi aholi ulushi ({km} km) bo‘yicha saralangan.")
    jadval = (
        f.sort_values(kol_pct, ascending=False)
        .head(10)[["nomi", kol_pct, kol_aholi, "aholi", "markazlar"]]
        .rename(columns={
            "nomi": "Tuman",
            kol_pct: "Uzoqdagi ulush, %",
            kol_aholi: "Uzoqdagi aholi",
            "aholi": "Jami aholi",
            "markazlar": "Markazlar",
        })
    )
    st.dataframe(
        jadval, hide_index=True,
        column_config={
            "Uzoqdagi ulush, %": st.column_config.NumberColumn(format="%.1f"),
            "Uzoqdagi aholi": st.column_config.NumberColumn(format="%d"),
            "Jami aholi": st.column_config.NumberColumn(format="%d"),
        },
    )

# ------------------------------------------------------------------
# 9. Manba va cheklovlar
# ------------------------------------------------------------------
st.divider()
st.caption(
    "**Manba:** loyiha ma’lumotlari — tuman chegaralari, «Inson» markazlari va 100 m aholi rastri.  \n"
    "**Cheklov 1:** masofa markazdan to‘g‘ri chiziq bo‘yicha (3 yoki 5 km radius) olingan, yo‘l bo‘ylab emas.  \n"
    "**Cheklov 2:** aholi soni rastrdan hisoblangan, shuning uchun rasmiy statistikadan biroz farq qilishi mumkin; "
    "tuman chegaralari xarita uchun soddalashtirilgan."
)
