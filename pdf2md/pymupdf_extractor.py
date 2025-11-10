import fitz
import os
import json


def extract_text_and_images(pdf_path, images_dir="images", save_json=None):
    os.makedirs(images_dir, exist_ok=True)
    doc = fitz.open(pdf_path)

    paragraphs, images = [], []
    for page_num, page in enumerate(doc, start=1):
        _extract_blocks(page, page_num, paragraphs, images, images_dir)

    result = {"paragraphs": paragraphs, "images": images}
    if save_json:
        with open(save_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def _extract_blocks(page, page_num, paragraphs, images, images_dir):
    for block in page.get_text("dict")["blocks"]:
        if block["type"] == 0:
            _extract_text_block(block, page_num, paragraphs)
        elif block["type"] == 1:
            _extract_image_block(block, page_num, images, images_dir)


def _extract_text_block(block, page_num, paragraphs):
    text = "\n".join(
        "".join(span.get("text", "") for span in line.get("spans", []))
        for line in block.get("lines", [])
    ).strip()
    if text:
        paragraphs.append({
            "page_num": page_num,
            "y0": round(block["bbox"][1], 2),
            "text": text,
            "md": text
        })


def _extract_image_block(block, page_num, images, images_dir):
    img_bytes = block["image"]
    image_id = f"page{page_num}_img{len(images)}"
    image_path = os.path.join(images_dir, f"{image_id}.png")
    with open(image_path, "wb") as f:
        f.write(img_bytes)
    images.append({
        "page_num": page_num,
        "y0": round(block["bbox"][1], 2),
        "name": image_id,
        "path": image_path
    })
