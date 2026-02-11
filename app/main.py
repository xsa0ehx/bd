import os
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
from sqlalchemy.exc import SQLAlchemyError
from app.routers import admin_audit
from app.routers import student, admin, test, user, admin_ui, admin_dashboard, ui_dashboard, admin_auth
from app.core.database import create_database
from app.routers.auth import router as auth_router
from app.routers.ui_auth import router as ui_auth_router
from app.core.confing import settings



# تنظیمات لاگ‌گیری
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
SWAGGER_OPENAPI_URL = "/openapi.json"
SWAGGER_TITLE = "سامانه مدیریت بسیج دانشجویی"
SWAGGER_OAUTH2_REDIRECT_URL = "/docs/oauth2-redirect"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    مدیریت عمر برنامه (Startup/Shutdown events).
    """
    # Startup
    logger.info("🚀 Starting Basij Management System...")

    # ایجاد جداول دیتابیس
    create_database()
    logger.info("✅ Database tables created/verified")

    # ایجاد نقش‌های پیش‌فرض
    await create_default_roles()

    yield

    # Shutdown
    logger.info("👋 Shutting down Basij Management System...")

async def create_default_roles():
    """ایجاد نقش‌های پیش‌فرض سیستم."""
    from app.core.database import SessionLocal
    from app.models.role import Role

    db = SessionLocal()
    try:

        default_roles = [
            {"name": "user", "description": "کاربر عادی سیستم"},
            {"name": "admin", "description": "مدیر سیستم با دسترسی کامل"},
            {"name": "moderator", "description": "ناظر سیستم"}
        ]

        for role_data in default_roles:
            role_name = role_data["name"]
            existing_role = db.query(Role).filter(Role.name == role_name).first()

            if not existing_role:
                role = Role(
                    name=role_name,
                    description=role_data["description"]
                )
                db.add(role)
                logger.info(f"✅ Created role: {role_name}")
            else:
                logger.info(f"ℹ️ Role already exists: {role_name}")

        db.commit()



    except SQLAlchemyError:
        db.rollback()
        logger.exception("❌ Database error while creating default roles")
        # برنامه را متوقف نکن، فقط خطا را لاگ کن
    finally:
        db.close()
# ایجاد برنامه FastAPI
app = FastAPI(
    title="سامانه مدیریت بسیج دانشجویی",
    description="سیستم احراز هویت بسیج دانشجویی",
    version="1.0.0",
    contact={
        "name": "تیم توسعه بسیج",
        "email": "basij@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=SWAGGER_OPENAPI_URL,
    openapi_tags=[
        {"name": "Authentication", "description": "عملیات احراز هویت و مدیریت کاربران"},
        {"name": "UI Authentication", "description": "صفحات وب برای احراز هویت"},
        {"name": "Test & Debug", "description": "Endpointهای تست و دیباگ"},
        {"name": "Users", "description": "مدیریت کاربران"},
    ]
)

# تنظیمات CORS
cors_allow_origins = list(settings.cors_allow_origins)
cors_allow_credentials = settings.cors_allow_credentials
if "*" in cors_allow_origins and cors_allow_credentials:
    logger.warning("CORS with wildcard origins cannot use credentials. Disabling credentials.")
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=list(settings.cors_allow_methods),
    allow_headers=list(settings.cors_allow_headers),
)

# Middleware برای لاگ‌گیری درخواست‌ها
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """لاگ تمام درخواست‌های ورودی."""
    start_time = time.time()
    response = None

    # اطلاعات درخواست
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    url = request.url.path

    logger.info(f"🌐 Request: {method} {url} from {client_host}")

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"❌ Error processing {method} {url}")
        raise

    process_time = time.time() - start_time
    if response is None:
        response = JSONResponse(
            status_code=500,
            content={"detail": "خطای داخلی سرور"},
        )
    response.headers["X-Process-Time"] = str(process_time)

    logger.info(f"✅ Response: {method} {url} - Status: {response.status_code} - Time: {process_time:.3f}s")

    return response


# سرویس فایل‌های استاتیک
static_dir = "app/static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"✅ Static files mounted at /static from {static_dir}")
else:
    logger.warning(f"⚠️ Directory {static_dir} does not exist. Static files disabled.")


# مدیریت خطاها
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """مدیریت خطاهای validation."""
    logger.warning(f"⚠️ Validation error: {exc.errors()}")

    return JSONResponse(
        status_code=422,
        content={
            "detail": "خطای اعتبارسنجی داده‌ها",
            "errors": exc.errors(),
            "body": exc.body
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """مدیریت خطاهای HTTP."""
    logger.warning(f"⚠️ HTTP error {exc.status_code}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        },
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """مدیریت خطاهای عمومی."""
    logger.exception("💥 Unhandled error")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "خطای داخلی سرور"
        },
    )


# صفحه اصلی
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root():
    """صفحه اصلی API."""
    return """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>سامانه مدیریت بسیج دانشجویی</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css" rel="stylesheet">
        <style>
            body { font-family: Vazirmatn, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .card { border-radius: 20px; border: none; }
            .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; }
        </style>
    </head>
    <body class="min-vh-100 d-flex align-items-center">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-8 col-lg-6">
                    <div class="card shadow-lg">
                        <div class="card-body text-center p-5">
                            <div class="mb-4">
                                <i class="bi bi-people-fill display-1 text-primary"></i>
                            </div>
                            <h1 class="display-4 mb-3 text-dark">سامانه مدیریت بسیج</h1>
                            <p class="lead mb-4 text-muted">
                                سیستم احراز هویت بسیج دانشجویی
                            </p>

                            <a href="/admin/login" class="btn btn-primary btn-lg px-4">
                                    <i class="bi bi-shield-lock me-2"></i>
                                    ورود مدیر
                                </a>
                                <a href="/ui-auth" class="btn btn-outline-primary btn-lg px-4">
                                    <i class="bi bi-display me-2"></i>
                                    رابط کاربری
                                </a>
                            </div>

                            <div class="row mt-5">
                                <div class="col-md-6">
                                    <div class="card border-0 bg-light">
                                        <div class="card-body">
                                            <h5><i class="bi bi-shield-check text-success"></i> امنیت بالا</h5>
                                            <p class="small text-muted">احراز هویت JWT و رمزنگاری پیشرفته</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 bg-light">
                                        <div class="card-body">
                                            <h5><i class="bi bi-speedometer2 text-primary"></i> عملکرد سریع</h5>
                                            <p class="small text-muted">پشتیبانی از هزاران کاربر همزمان</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="mt-4 text-muted small">
                                <p>نسخه ۱.۰.۰ | توسعه‌یافته با FastAPI و Python</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


# اطلاعات API
@app.get("/api/info", tags=["System"])
async def get_api_info():
    """دریافت اطلاعات کلی API."""
    return {
        "name": "سامانه مدیریت بسیج دانشجویی",
        "version": "1.0.0",
        "description": "سیستم احراز هویت بسیج دانشجویی",
        "status": "active",
        "author": "تیم توسعه بسیج",
        "endpoints": {
            "authentication": "/auth",
            "ui_authentication": "/ui-auth",
            "user_management": "/users",
            "testing": "/test",
            "admin_portal": "/admin/login"
        },
        "database": {
            "type": "SQLite",
            "status": "connected"
        },
        "security": {
            "authentication": "JWT",
            "password_hashing": "bcrypt"
        }
    }


# سلامت سیستم
@app.get("/health", tags=["System"])
async def health_check():
    """بررسی سلامت سیستم."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "basij-management-system",
        "version": "1.0.0"
    }




# شامل کردن routerها
app.include_router(auth_router)
app.include_router(test.router)
app.include_router(ui_auth_router)
app.include_router(user.router)
app.include_router(student.router)
app.include_router(admin.router)
app.include_router(admin_ui.router)
app.include_router(admin_auth.router)
app.include_router(admin_dashboard.router)
app.include_router(ui_dashboard.router)
app.include_router(admin_audit.router)


from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=SWAGGER_OPENAPI_URL,
        title=SWAGGER_TITLE + " - Swagger UI",
        oauth2_redirect_url=SWAGGER_OAUTH2_REDIRECT_URL,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get(SWAGGER_OAUTH2_REDIRECT_URL, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=SWAGGER_OPENAPI_URL,
        title=SWAGGER_TITLE + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )