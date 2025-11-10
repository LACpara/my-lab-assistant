import os
import shutil
import pdf2md

if __name__ == "__main__":

    PDF_PATH = "./sample.pdf"
    outputdir = "./output"
    if os.path.exists(outputdir):
        shutil.rmtree(outputdir)
    os.mkdir(outputdir)

    doc_save_json = os.path.join(outputdir, "docling_result.json")
    doc_save_pickle = os.path.join(outputdir, "docling_document.pkl")
    images_dir = os.path.join(outputdir, "images")
    img_save_json = os.path.join(outputdir, "pymupdf_cache.json")
    structured_content_output_path = os.path.join(outputdir, "structured_pages_with_tables.json")
    final_markdown_output_path = os.path.join(outputdir, "merged_pages_output.md")

    # Step 1: Docling 解析
    doc = pdf2md.parse_pdf_with_docling(PDF_PATH, save_json=doc_save_json, save_pickle=doc_save_pickle)

    # Step 2: PyMuPDF 提取
    cache = pdf2md.extract_text_and_images(PDF_PATH, images_dir=images_dir, save_json=img_save_json)
    paragraphs = cache["paragraphs"]
    images = cache["images"]

    # Step 3: 合并
    structured_pages = pdf2md.merge_text_images_tables(doc, paragraphs, images)
    pdf2md.save_structured_pages(structured_pages, structured_content_output_path)

    # Step 4: 生成 Markdown
    pdf2md.structured_pages_to_md(structured_pages, final_markdown_output_path)
