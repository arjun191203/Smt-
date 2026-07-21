"""
Builds SMT_Dashboard_Data.xlsx - the data-entry template for the SMT dashboard.
Run once to (re)generate a blank template with headers, example rows, and a legend.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=10)
EXAMPLE_FILL = PatternFill("solid", fgColor="FFF9DB")  # yellow-ish = "edit / example row"
TITLE_FONT = Font(name=FONT, bold=True, size=13, color="1F2937")
NOTE_FONT = Font(name=FONT, italic=True, size=9, color="6B7280")
THIN = Side(style="thin", color="D1D5DB")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

wb = openpyxl.Workbook()
wb.remove(wb.active)


def make_sheet(name, headers, example_rows, col_widths=None, note=None):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    # header row at row 1
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[1].height = 28
    # example rows (yellow = fill these in / overwrite with real data)
    for r, row in enumerate(example_rows, start=2):
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font = Font(name=FONT, size=10)
            cell.fill = EXAMPLE_FILL
            cell.border = BORDER
            cell.alignment = Alignment(horizontal="center")
    # column widths
    widths = col_widths or [16] * len(headers)
    for c, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    if note:
        note_row = len(example_rows) + 3
        ws.cell(row=note_row, column=1, value=note).font = NOTE_FONT
    ws.freeze_panes = "A2"
    return ws


# 1. Lines config -----------------------------------------------------------
make_sheet(
    "Lines",
    ["Line_Name", "Model_Running", "Target_UPH", "Shift"],
    [
        ["SMT-L1", "PCB-A203", 850, "Day"],
        ["SMT-L2", "PCB-B110", 720, "Day"],
        ["SMT-L3", "PCB-C450", 600, "Night"],
    ],
    col_widths=[16, 18, 14, 12],
)

# 2. Day Plan vs Actual -------------------------------------------------------
make_sheet(
    "DayPlan",
    ["Date", "Line", "Model", "Shift", "Plan_Qty", "Actual_Qty"],
    [
        ["2026-07-21", "SMT-L1", "PCB-A203", "Day", 5000, 4910],
        ["2026-07-21", "SMT-L2", "PCB-B110", "Day", 4200, 4106],
        ["2026-07-21", "SMT-L3", "PCB-C450", "Night", 3600, 3350],
    ],
    col_widths=[12, 12, 14, 10, 12, 12],
    note="One row per Line per Date. Achievement % is calculated automatically by the dashboard.",
)

# 3. Hourly Output (all lines) ------------------------------------------------
make_sheet(
    "HourlyOutput",
    ["Date", "Line", "Hour_Slot", "Plan_Qty", "Actual_Qty", "Pass_Qty", "Fail_Qty"],
    [
        ["2026-07-21", "SMT-L1", "07:00-08:00", 630, 610, 598, 12],
        ["2026-07-21", "SMT-L1", "08:00-09:00", 630, 640, 630, 10],
        ["2026-07-21", "SMT-L2", "07:00-08:00", 525, 500, 490, 10],
    ],
    col_widths=[12, 12, 14, 12, 12, 12, 12],
    note="One row per Line per hour slot. Hour_Slot must use format HH:MM-HH:MM (e.g. 07:00-08:00) so the dashboard sorts it correctly.",
)

# 4. Mounter details -----------------------------------------------------------
make_sheet(
    "MounterDetails",
    ["Date", "Line", "Machine_No", "Model_Placed", "Placement_Qty",
     "CPH_Target", "CPH_Actual", "Pickup_Error_Qty", "Downtime_Min"],
    [
        ["2026-07-21", "SMT-L1", "Mounter-1", "PCB-A203", 128000, 42000, 40500, 35, 12],
        ["2026-07-21", "SMT-L1", "Mounter-2", "PCB-A203", 118500, 40000, 39800, 21, 5],
    ],
    col_widths=[12, 10, 12, 14, 14, 12, 12, 14, 12],
    note="One row per mounter machine per line per day. CPH = components per hour.",
)

# 5. AOI details --------------------------------------------------------------
make_sheet(
    "AOIDetails",
    ["Date", "Line", "AOI_No", "Inspected_Qty", "Pass_Qty", "NG_Qty", "FalseCall_Qty"],
    [
        ["2026-07-21", "SMT-L1", "AOI-1", 4910, 4780, 130, 45],
        ["2026-07-21", "SMT-L2", "AOI-1", 4106, 3990, 116, 30],
    ],
    col_widths=[12, 10, 10, 14, 12, 10, 14],
    note="One row per AOI machine per line per day. First Pass Yield % is calculated automatically.",
)

# 6. Line hourly UPH ------------------------------------------------------------
make_sheet(
    "UPH_Hourly",
    ["Date", "Line", "Hour_Slot", "UPH_Target", "UPH_Actual"],
    [
        ["2026-07-21", "SMT-L1", "07:00-08:00", 850, 810],
        ["2026-07-21", "SMT-L1", "08:00-09:00", 850, 860],
        ["2026-07-21", "SMT-L2", "07:00-08:00", 720, 690],
    ],
    col_widths=[12, 12, 14, 12, 12],
    note="UPH = units per hour, per line, per hour slot.",
)

# 7. Solder paste timing ---------------------------------------------------------
make_sheet(
    "SolderPaste",
    ["Date", "Line", "Paste_Batch_No", "Print_Start_Time", "Print_End_Time",
     "Room_Temp_Out_Time", "Expiry_Time", "Viscosity_Check_Time"],
    [
        ["2026-07-21", "SMT-L1", "SP-2607-01", "06:45", "10:30", "06:30", "14:30", "09:00"],
        ["2026-07-21", "SMT-L2", "SP-2607-02", "06:50", "10:45", "06:35", "14:35", "09:05"],
    ],
    col_widths=[12, 10, 16, 16, 16, 18, 14, 20],
    note="All times in 24h HH:MM. Expiry_Time is when the paste must be discarded/replaced (typically 4-8h after Room_Temp_Out_Time).",
)

# 8. Stencil cleaning timing ------------------------------------------------------
make_sheet(
    "StencilCleaning",
    ["Date", "Line", "Stencil_ID", "Last_Clean_Time", "Next_Due_Time",
     "Cycles_Since_Clean", "Cleaning_Method"],
    [
        ["2026-07-21", "SMT-L1", "STN-A203-01", "07:00", "11:00", 15, "Auto-wipe"],
        ["2026-07-21", "SMT-L2", "STN-B110-01", "07:10", "11:10", 12, "Manual"],
    ],
    col_widths=[12, 10, 16, 16, 16, 18, 16],
    note="Cleaning is usually due every N print cycles - track Cycles_Since_Clean so the dashboard can flag when it's near due.",
)

# Legend / instructions sheet, placed first
legend = wb.create_sheet("READ ME - Legend", 0)
legend.sheet_view.showGridLines = False
legend.column_dimensions["A"].width = 100
lines = [
    ("SMT DASHBOARD - DATA ENTRY WORKBOOK", TITLE_FONT),
    ("", None),
    ("HOW TO USE THIS FILE", Font(name=FONT, bold=True, size=11)),
    ("1. Each tab below is one data table. Yellow rows are EXAMPLES - overwrite/replace them with real data, keep the same columns.", Font(name=FONT, size=10)),
    ("2. Add a new row for every new date / line / hour / machine - do not overwrite old rows, the dashboard needs history.", Font(name=FONT, size=10)),
    ("3. Keep Line_Name spelling identical across every tab (e.g. always 'SMT-L1', not 'Line 1' in one tab and 'SMT-L1' in another).", Font(name=FONT, size=10)),
    ("4. Dates in YYYY-MM-DD, times in 24h HH:MM.", Font(name=FONT, size=10)),
    ("5. Save the file (Ctrl+S) - the dashboard reads it live, no need to close Excel or restart the app.", Font(name=FONT, size=10)),
    ("", None),
    ("TABS", Font(name=FONT, bold=True, size=11)),
    ("Lines            - list of SMT lines, their current model and UPH target", Font(name=FONT, size=10)),
    ("DayPlan          - daily plan vs actual output per line", Font(name=FONT, size=10)),
    ("HourlyOutput     - hour-by-hour output for the all-lines graph", Font(name=FONT, size=10)),
    ("MounterDetails   - per-line mounter machine performance", Font(name=FONT, size=10)),
    ("AOIDetails       - per-line AOI inspection results", Font(name=FONT, size=10)),
    ("UPH_Hourly       - per-line hourly UPH graph data", Font(name=FONT, size=10)),
    ("SolderPaste      - solder paste print/expiry timings", Font(name=FONT, size=10)),
    ("StencilCleaning  - stencil cleaning timings", Font(name=FONT, size=10)),
]
for i, (text, font) in enumerate(lines, start=1):
    cell = legend.cell(row=i, column=1, value=text)
    if font:
        cell.font = font

wb.save("/home/claude/smt_dashboard/data/SMT_Dashboard_Data.xlsx")
print("saved")
