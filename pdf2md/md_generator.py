def structured_pages_to_md(structured_pages, output_md_path):
    lines = ["# 文档合并结果\n\n"]
    for page in structured_pages:
        lines.extend(_render_page_md(page))
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _render_page_md(page):
    lines = [f"<!-- page {page.get('page', 'unknown')} begin -->\n\n"]
    if page.get("content"):
        lines.append(page["content"] + "\n\n")

    if page.get("images"):
        lines.append("<!-- images -->\n\n")
        for img in page["images"]:
            uri = img.get("url", "").replace("\\", "/")
            alt = img.get("id", "image")
            lines.append(f"![{alt}]({uri})\n\n")

    if page.get("tables"):
        lines.append("<!-- tables -->\n\n")
        for tb in page["tables"]:
            content = tb.get("content", "").strip()
            if content:
                lines.append(content + "\n\n")

    lines.append(f"<!-- page {page.get('page', 'unknown')} end -->\n\n")
    return lines
