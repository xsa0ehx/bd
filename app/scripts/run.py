from pathlib import Path
import sys
import uvicorn


if __name__ == "__main__":
    # اضافه کردن مسیر پروژه
    # Ensure the project root (parent of ``app``) is on PYTHONPATH.
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

    # اجرای سرور
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8011,
        reload=True,
        log_level="info",
    )