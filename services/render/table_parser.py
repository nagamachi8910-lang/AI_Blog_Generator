def parse_markdown_table(content: str) -> tuple:
    """
    Parses a markdown table string using pipe ('|') separators.
    Returns a tuple of (headers: list of str, rows: list of list of str).
    """
    content = (content or "").strip()
    if not content:
        return [], []

    raw_lines = content.splitlines()
    lines = [line.strip() for line in raw_lines if line.strip()]
    if not lines:
        return [], []

    headers = []
    rows = []

    for line in lines:
        cells = [c.strip() for c in line.split("|")]
        
        # Normalize by removing leading/trailing pipe cells
        if line.startswith("|"):
            cells = cells[1:]
        if line.endswith("|"):
            cells = cells[:-1]

        # Skip empty lines
        if not cells:
            continue

        # Skip table divider format lines, e.g. |:---:|---|:---
        is_divider = all(
            all(char in ("-", ":", " ") for char in cell) and cell.strip() != ""
            for cell in cells
        )
        if is_divider:
            continue

        if not headers:
            headers = cells
        else:
            rows.append(cells)

    return headers, rows
