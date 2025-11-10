import json
import re
from difflib import SequenceMatcher


def merge_text_images_tables(doc, paragraphs, images):
    page_texts = _map_docling_to_pages(doc, paragraphs)
    sturctured_pages = _build_structured_pages(page_texts, images)
    return sturctured_pages


def _map_docling_to_pages(doc, paragraphs):
    doc_markdown = re.sub(r'<!--\s*image\s*-->', '', doc.export_to_markdown(strict_text=True))
    blocks = [p.strip() for p in doc_markdown.split("\n\n") if p.strip()]

    candidates = [_best_page_for_block(blk, paragraphs) for blk in blocks]
    smoothed_pages = _smooth_pages(candidates)

    pages = {}
    for blk, pg in zip(blocks, smoothed_pages):
        pages.setdefault(pg, []).append(blk)
    return pages


def _best_page_for_block(block, paragraphs):
    best_page, best_score = 1, 0
    for para in paragraphs:
        score = SequenceMatcher(None, block, para["text"]).ratio()
        if score > best_score:
            best_page, best_score = para["page_num"], score
    return best_page


def _smooth_pages(candidates):
    smoothed = []
    for i, p in enumerate(candidates):
        if i > 0 and abs(p - smoothed[-1]) > 1:
            smoothed.append(smoothed[-1] + 1)
        else:
            smoothed.append(p)
    return smoothed


def _build_structured_pages(page_texts, images):
    table_pattern = re.compile(r"(\|.*\|(?:\n\|.*\|)+)", re.MULTILINE)
    structured = []

    all_pages = sorted(set(page_texts.keys()) | {img["page_num"] for img in images})
    for page_num in all_pages:
        page_md = "\n\n".join(page_texts.get(page_num, []))
        tables, page_md_no_tables = _extract_tables(page_md, table_pattern, page_num)

        imgs_in_page = sorted([img for img in images if img["page_num"] == page_num], key=lambda x: x["y0"])
        img_records = [{"id": f"img_{page_num}_{i}", "url": img["path"]} for i, img in enumerate(imgs_in_page)]

        structured.append({
            "page": page_num,
            "content": page_md_no_tables.strip(),
            "images": img_records,
            "tables": tables
        })
    return structured


def _extract_tables(page_md, pattern, page_num):
    tables = []
    def _replacer(match):
        table_id = f"tbl_{page_num}_{len(tables)}"
        tables.append({"id": table_id, "content": match.group(1).strip()})
        return ""
    md_no_tables = re.sub(pattern, _replacer, page_md)
    return tables, md_no_tables


def save_structured_pages(structured_pages, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured_pages, f, ensure_ascii=False, indent=2)
