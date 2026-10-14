import io

import pandas as pd
from fpdf import FPDF, XPos, YPos

MAX_CELL_CHARS = 40
ROW_HEIGHT = 7
FONT_SIZE = 8


def rows_to_excel_bytes(rows: list[dict]) -> bytes:
    """Renders rows (list of {column: value} dicts, as returned by a
    BaseDBAdapter.run_query) to an .xlsx file's raw bytes."""
    df = pd.DataFrame(rows)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def rows_to_pdf_bytes(rows: list[dict], title: str = "Report") -> bytes:
    """Renders rows to a simple landscape-table PDF's raw bytes. Paginates
    long results and re-prints the header row on each new page."""
    df = pd.DataFrame(rows)
    columns = list(df.columns)

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    page_width = pdf.w - 2 * pdf.l_margin
    col_width = page_width / max(len(columns), 1)

    def draw_header():
        pdf.set_font("Helvetica", "B", FONT_SIZE)
        for col in columns:
            pdf.cell(col_width, ROW_HEIGHT, str(col)[:MAX_CELL_CHARS], border=1)
        pdf.ln(ROW_HEIGHT)
        pdf.set_font("Helvetica", "", FONT_SIZE)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    draw_header()

    bottom_limit = pdf.h - pdf.b_margin
    for _, row in df.iterrows():
        if pdf.get_y() + ROW_HEIGHT > bottom_limit:
            pdf.add_page()
            draw_header()
        for col in columns:
            pdf.cell(col_width, ROW_HEIGHT, str(row[col])[:MAX_CELL_CHARS], border=1)
        pdf.ln(ROW_HEIGHT)

    return bytes(pdf.output())
