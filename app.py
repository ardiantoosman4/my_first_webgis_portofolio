from flask import Flask, render_template, request
import folium
import requests
import pandas
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

app = Flask(__name__)
app.url_map.strict_slashes = False

# Load data once
df = pd.read_csv("./static/earthquake_data.csv")
df = df[df["mag"] > 5]  # Filter for magnitude > 5

# Precompute ranges
min_lat = round(df['latitude'].min(), 2)
max_lat = round(df['latitude'].max(), 2)
min_lon = round(df['longitude'].min(), 2)
max_lon = round(df['longitude'].max(), 2)
min_depth = round(df['depth'].min(), 2)
max_depth = round(df['depth'].max(), 2)
min_mag = round(df['mag'].min(), 2)
max_mag = round(df['mag'].max(), 2)

# Function: color by depth
cmap = plt.get_cmap("gist_rainbow")
norm = mpl.colors.Normalize(vmin=20, vmax=100)

def depth_to_color(depth):
    rgba = cmap(norm(depth))
    return mpl.colors.to_hex(rgba)

def scale_marker(mag, min_size=3, max_size=15):
    scale = (mag - min_mag) / (max_mag - min_mag)
    return int(min_size + scale * (max_size - min_size))

@app.route("/")
def index():
    return render_template("home.html")

@app.route("/project1", methods=["GET", "POST"])
def project1():
    # Default filters
    filters = {
        "min_lat": float(request.form.get("min_lat", min_lat)),
        "max_lat": float(request.form.get("max_lat", max_lat)),
        "min_lon": float(request.form.get("min_lon", min_lon)),
        "max_lon": float(request.form.get("max_lon", max_lon)),
        "min_depth": float(request.form.get("min_depth", min_depth)),
        "max_depth": float(request.form.get("max_depth", max_depth)),
        "min_mag": float(request.form.get("min_mag", min_mag)),
    }

    # Apply filters
    filtered = df[
        (df["latitude"] >= filters["min_lat"]) &
        (df["latitude"] <= filters["max_lat"]) &
        (df["longitude"] >= filters["min_lon"]) &
        (df["longitude"] <= filters["max_lon"]) &
        (df["depth"] >= filters["min_depth"]) &
        (df["depth"] <= filters["max_depth"]) &
        (df["mag"] >= filters["min_mag"])
    ]

    # Create folium map
    start_location = [filtered["latitude"].median(), filtered["longitude"].mean()] if len(filtered) else [0,0]
    m = folium.Map(location=start_location, zoom_start=6, tiles='Esri.WorldImagery')

    for _, row in filtered.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=scale_marker(row["mag"]),
            color="black",
            weight=0.3,
            fill=True,
            fill_color=depth_to_color(row["depth"]),
            fill_opacity=0.8,
            popup=folium.Popup(
                f"""
                <b>Magnitude:</b> {row['mag']} {row['magType']}<br>
                <b>Place:</b> {row['place']}<br>
                <b>Time:</b> {row['time']}<br>
                <b>Latitude:</b> {row['latitude']}°<br>
                <b>Longitude:</b> {row['longitude']}°<br>
                <b>Depth:</b> {row['depth']} km
                """,
                max_width=300
            )
        ).add_to(m)

    # Export map as HTML string
    map_html = m._repr_html_()

    return render_template(
        "project1.html",
        filters=filters,
        map_html=map_html,
        ranges={
            "min_lat": -90, "max_lat": 90,
            "min_lon": -180, "max_lon": 180,
            "min_depth": 0, "max_depth": 1000,
            "min_mag": 5, "max_mag": 10
        },
    )

@app.route("/project2")
def project2():
    source_url = "https://raw.githubusercontent.com/python-visualization/folium-example-data/main/us_states.json"
    geo_json_data = requests.get(source_url).json()
    state_data  = pandas.read_csv("./static/us_county_data.csv")
    state_data["Unemployment"] = pandas.to_numeric(state_data["Unemployment"], errors="coerce")
    state_data.dropna(inplace=True)
    state_totals = state_data.groupby('State')['Unemployment'].sum().reset_index()
    state_totals["LogUnemployment"] = np.log10(state_totals["Unemployment"])

    state_dict = state_totals.set_index("State").to_dict(orient="index")
    for feature in geo_json_data["features"]:
        state_id = feature["id"]
        if state_id in state_dict:
            feature["properties"]["Unemployment"] = state_dict[state_id]["Unemployment"]
            feature["properties"]["LogUnemployment"] = state_dict[state_id]["LogUnemployment"]
        else:
            feature["properties"]["Unemployment"] = "No data"
            feature["properties"]["LogUnemployment"] = "No data"

    m = folium.Map([43, -100], zoom_start=5)
    folium.Choropleth(
        geo_data=geo_json_data,
        data=state_totals,
        columns=["State", "LogUnemployment"],
        key_on="feature.id",
        fill_color="viridis",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Log Total Unemployment",
        highlight=True,
    ).add_to(m)

    folium.GeoJson(
        geo_json_data,
        style_function=lambda feature: {"fillOpacity": 0, "color": "transparent"},
        popup=folium.GeoJsonPopup(
            fields=["name", "Unemployment", "LogUnemployment"],
            aliases=["State:", "Total Unemployment:", "Log(Unemployment):"],
            localize=True
        )
    ).add_to(m)

    map_html = m._repr_html_()
    return render_template("project2.html", map_html=map_html)

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)
