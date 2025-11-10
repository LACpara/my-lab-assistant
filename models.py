from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone


db = SQLAlchemy()


class PDFFile(db.Model):
    __tablename__ = "pdf_files"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_hash = db.Column(db.String(64), unique=True, nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    
    status = db.Column(db.String(32), default="pending")  # pending, processing, completed, failed
    uploaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # 结果文件
    md_path = db.Column(db.String(512), nullable=True)
    structured_json_path = db.Column(db.String(512), nullable=True)
    images_dir = db.Column(db.String(512), nullable=True)
    
    # 调试模式中间结果（可为空）
    docling_json_path = db.Column(db.String(512), nullable=True)
    docling_pickle_path = db.Column(db.String(512), nullable=True)
    pymupdf_cache_json = db.Column(db.String(512), nullable=True)

    progress = db.Column(db.Integer, default=0)  # 0~100 %

    def __repr__(self):
        return f"<PDFFile {self.filename} ({self.status})>"