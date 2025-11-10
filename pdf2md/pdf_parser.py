import json
import pickle
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def parse_pdf_with_docling(pdf_path, do_ocr=False, save_json=None, save_pickle=None):
    """
    使用 Docling 提取 PDF 文档结构
    """
    doc = _convert_pdf(pdf_path, do_ocr)
    _save_outputs(doc, save_json, save_pickle)
    return doc


def _convert_pdf(pdf_path, do_ocr):
    options = PdfPipelineOptions()
    options.do_ocr = do_ocr
    options.do_table_structure = True
    options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options, render_pages=True)}
    )
    return converter.convert(pdf_path).document


def _save_outputs(doc, save_json, save_pickle):
    if save_json:
        with open(save_json, "w", encoding="utf-8") as f:
            json.dump(doc.model_dump(), f, ensure_ascii=False, indent=2)
    if save_pickle:
        with open(save_pickle, "wb") as f:
            pickle.dump(doc, f)
