from dbchat.reports.export import rows_to_excel_bytes, rows_to_pdf_bytes


def test_rows_to_excel_bytes_is_valid_xlsx():
    rows = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]

    data = rows_to_excel_bytes(rows)

    assert data[:2] == b"PK"  # .xlsx is a zip archive


def test_rows_to_pdf_bytes_is_valid_pdf():
    rows = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]

    data = rows_to_pdf_bytes(rows, title="Test")

    assert data[:4] == b"%PDF"


def test_rows_to_pdf_bytes_paginates_long_results():
    import io

    from pypdf import PdfReader

    small = rows_to_pdf_bytes([{"id": 1}], title="Small")
    big = rows_to_pdf_bytes([{"id": i, "value": f"row {i}"} for i in range(300)], title="Big")

    assert len(PdfReader(io.BytesIO(small)).pages) == 1
    assert len(PdfReader(io.BytesIO(big)).pages) > 1
