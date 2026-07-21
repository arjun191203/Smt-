"""
SMT Line Dashboard - local server.

Run:   python app.py
Then open http://<this-computer's-IP>:5000 on your phone (same WiFi).

It reads data/SMT_Dashboard_Data.xlsx fresh on every request (based on the
file's last-modified time), so you just edit + save the Excel file and
refresh the browser - no restart needed.
"""
import os
import time
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, render_template, request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(APP_DIR, "data", "SMT_Dashboard_Data.xlsx")

app = Flask(__name__)

_cache = {"mtime": None, "sheets": None}


def load_sheets():
    """Reload the workbook only if the file changed on disk since last read."""
    mtime = os.path.getmtime(EXCEL_PATH)
    if _cache["mtime"] != mtime:
        sheets = pd.read_excel(EXCEL_PATH, sheet_name=None, engine="openpyxl")
        for name, df in sheets.items():
            df.columns = [str(c).strip() for c in df.columns]
            df.dropna(how="all", inplace=True)
            if "Date" in df.columns:
                # coerce so stray note/legend text rows (not valid dates) become NaT and get dropped
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df.dropna(subset=["Date"], inplace=True)
                df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
            elif "Line_Name" in df.columns:
                # Lines sheet has no Date column - drop any stray text/legend rows instead
                df.dropna(subset=["Target_UPH"], inplace=True)
            sheets[name] = df
        _cache["mtime"] = mtime
        _cache["sheets"] = sheets
    return _cache["sheets"]


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def filt(df, date, line=None):
    out = df[df["Date"] == date] if "Date" in df.columns else df
    if line is not None and "Line" in out.columns:
        out = out[out["Line"] == line]
    return out


def sort_by_hour(df):
    if "Hour_Slot" not in df.columns or df.empty:
        return df
    return df.assign(_h=df["Hour_Slot"].str[:5]).sort_values("_h").drop(columns="_h")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/meta")
def api_meta():
    sheets = load_sheets()
    lines_df = sheets["Lines"]
    dates = set()
    for name in ["DayPlan", "HourlyOutput"]:
        if "Date" in sheets[name].columns:
            dates |= set(sheets[name]["Date"].dropna().unique().tolist())
    return jsonify({
        "lines": lines_df.to_dict(orient="records"),
        "dates": sorted(dates, reverse=True),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/overview")
def api_overview():
    date = request.args.get("date", today_str())
    sheets = load_sheets()

    dayplan = filt(sheets["DayPlan"], date)
    totals = {
        "plan_qty": int(dayplan["Plan_Qty"].sum()) if not dayplan.empty else 0,
        "actual_qty": int(dayplan["Actual_Qty"].sum()) if not dayplan.empty else 0,
    }
    totals["achievement_pct"] = (
        round(100 * totals["actual_qty"] / totals["plan_qty"], 1) if totals["plan_qty"] else 0
    )

    by_line = []
    for _, row in dayplan.iterrows():
        plan, actual = row["Plan_Qty"], row["Actual_Qty"]
        by_line.append({
            "line": row["Line"],
            "model": row.get("Model", ""),
            "shift": row.get("Shift", ""),
            "plan_qty": int(plan),
            "actual_qty": int(actual),
            "achievement_pct": round(100 * actual / plan, 1) if plan else 0,
        })

    hourly = filt(sheets["HourlyOutput"], date)
    hourly = sort_by_hour(hourly)
    hour_slots = sorted(hourly["Hour_Slot"].unique().tolist(), key=lambda h: h[:5]) if not hourly.empty else []
    series = []
    for line in sorted(hourly["Line"].unique().tolist()) if not hourly.empty else []:
        line_df = hourly[hourly["Line"] == line].set_index("Hour_Slot")
        series.append({
            "line": line,
            "actual": [int(line_df.loc[h, "Actual_Qty"]) if h in line_df.index else 0 for h in hour_slots],
            "plan": [int(line_df.loc[h, "Plan_Qty"]) if h in line_df.index else 0 for h in hour_slots],
        })

    return jsonify({
        "date": date, "totals": totals, "by_line": by_line,
        "hourly": {"hour_slots": hour_slots, "series": series},
    })


@app.route("/api/line/<line>")
def api_line(line):
    date = request.args.get("date", today_str())
    sheets = load_sheets()

    uph = sort_by_hour(filt(sheets["UPH_Hourly"], date, line))
    mounters = filt(sheets["MounterDetails"], date, line)
    aoi = filt(sheets["AOIDetails"], date, line)
    aoi = aoi.copy()
    if not aoi.empty:
        aoi["FPY_pct"] = (100 * aoi["Pass_Qty"] / aoi["Inspected_Qty"]).round(1)
    paste = filt(sheets["SolderPaste"], date, line)
    stencil = filt(sheets["StencilCleaning"], date, line)

    return jsonify({
        "line": line,
        "date": date,
        "uph": {
            "hour_slots": uph["Hour_Slot"].tolist() if not uph.empty else [],
            "target": uph["UPH_Target"].tolist() if not uph.empty else [],
            "actual": uph["UPH_Actual"].tolist() if not uph.empty else [],
        },
        "mounters": mounters.to_dict(orient="records"),
        "aoi": aoi.to_dict(orient="records"),
        "solder_paste": paste.to_dict(orient="records"),
        "stencil_cleaning": stencil.to_dict(orient="records"),
    })


if __name__ == "__main__":
    # host 0.0.0.0 so it's reachable from your phone / from Render.
    # Render sets the PORT env var; locally it falls back to 5000.
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
