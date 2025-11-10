import os
import sys
import click
import hashlib
import threading

from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from models import db, PDFFile
from celery import Celery
from datetime import datetime

from pdf2md import (
    parse_pdf_with_docling,
    extract_text_and_images,
    merge_text_images_tables,
    save_structured_pages,
    structured_pages_to_md
)


UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
DEBUG_MODE = True  # 可通过配置控制

app = Flask(__name__)
app.secret_key = "secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///pdf_files.db"
db.init_app(app)

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# #### 控制并发 
# - 避免同时多个请求触发 Docling 初始化：
# - 使用 队列（如 Celery、RQ）异步处理上传文件
# - 或者在 Flask 内部使用 线程锁，确保 Docling 模型下载/加载阶段只有一个线程执行：
# 控制模型只下载一次
model_preload_done = False
model_lock = threading.Lock()

def preload_model_background():
    from pdf2md.pdf_parser import predownload_docling_model
    global model_preload_done
    with model_lock:
        if not model_preload_done:
            print("⏳ 后台线程预下载 Docling 模型中...")
            predownload_docling_model()
            print("✅ Docling 模型预下载完成！")
            model_preload_done = True

# 只在 Flask 服务启动时执行，不在 CLI 命令触发
if os.environ.get("FLASK_RUN_FROM_CLI") == "true":
    threading.Thread(target=preload_model_background, daemon=True).start()


@app.cli.command("init-db")
@click.option('--drop', is_flag=True, help='Create after drop.')
def init_db(drop):
    """初始化数据库（创建表）"""
    with app.app_context():
        if drop:
            db.drop_all()
        db.create_all()
        click.echo("✅ 数据库初始化完成！")


def sha256_file(filepath):
    hash_obj = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        if not uploaded_file:
            flash("未选择文件")
            return redirect(request.url)

        file_path = os.path.join(UPLOAD_DIR, uploaded_file.filename)
        uploaded_file.save(file_path)
        file_hash = sha256_file(file_path)

        existing = PDFFile.query.filter_by(file_hash=file_hash).first()
        if existing:
            flash(f"文件 {uploaded_file.filename} 已存在，忽略处理")
            os.remove(file_path)
            return redirect(request.url)

        # 添加数据库记录
        pdf_record = PDFFile(
            filename=uploaded_file.filename,
            file_hash=file_hash,
            file_path=file_path,
            status="processing"
        )
        db.session.add(pdf_record)
        db.session.commit()

        # 处理文件
        try:
            process_pdf_file(pdf_record)
            flash(f"文件 {uploaded_file.filename} 处理完成")
        except Exception as e:
            pdf_record.status = "failed"
            db.session.commit()
            flash(f"文件 {uploaded_file.filename} 处理失败: {e}")
        return redirect(url_for("index"))

    # GET 方法
    files = PDFFile.query.order_by(PDFFile.uploaded_at.desc()).all()
    return render_template("index.html", files=files)

def process_pdf_file(pdf_record):
    filename_no_ext = os.path.splitext(pdf_record.filename)[0]
    output_base_dir = os.path.join(OUTPUT_DIR, filename_no_ext)
    os.makedirs(output_base_dir, exist_ok=True)

    # -------------------- PDF2MD 流程 --------------------
    debug_paths = {}  # 中间结果路径

    ## 这样即使两个页面同时上传，也不会在 Docling 初始化阶段同时发起网络请求，避免 SSL EOF 错误。
    with model_lock:
        if DEBUG_MODE:
            docling_json = os.path.join(output_base_dir, "docling_result.json")
            docling_pickle = os.path.join(output_base_dir, "docling_document.pkl")
            pdf_cache = os.path.join(output_base_dir, "pymupdf_cache.json")
            debug_paths.update({
                "docling_json_path": docling_json,
                "docling_pickle_path": docling_pickle,
                "pymupdf_cache_json": pdf_cache
            })
            doc = parse_pdf_with_docling(pdf_record.file_path, save_json=docling_json, save_pickle=docling_pickle)
            cache = extract_text_and_images(pdf_record.file_path, images_dir=os.path.join(output_base_dir, "images"), save_json=pdf_cache)
        else:
            doc = parse_pdf_with_docling(pdf_record.file_path)
            cache = extract_text_and_images(pdf_record.file_path, images_dir=os.path.join(output_base_dir, "images"))

    # 合并
    structured_pages = merge_text_images_tables(doc, cache["paragraphs"], cache["images"])
    structured_json = os.path.join(output_base_dir, "structured_pages.json")
    md_file = os.path.join(output_base_dir, f"{filename_no_ext}.md")
    save_structured_pages(structured_pages, structured_json)
    structured_pages_to_md(structured_pages, md_file)

    # 更新数据库记录
    pdf_record.status = "completed"
    pdf_record.processed_at = datetime.utcnow()
    pdf_record.md_path = md_file
    pdf_record.structured_json_path = structured_json
    pdf_record.images_dir = os.path.join(output_base_dir, "images")
    if DEBUG_MODE:
        pdf_record.docling_json_path = debug_paths["docling_json_path"]
        pdf_record.docling_pickle_path = debug_paths["docling_pickle_path"]
        pdf_record.pymupdf_cache_json = debug_paths["pymupdf_cache_json"]

    db.session.commit()