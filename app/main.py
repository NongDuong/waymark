from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from . import models
import redis.asyncio as aioredis
from fastapi_limiter import FastAPILimiter

from .api import auth, memories, map, social, places, discovery, media, profile, chat, collections, reports, admin

# Base.metadata.create_all(bind=engine) # We use alembic instead

app = FastAPI(
    title="Waymark API",
    description="Backend API for Waymark memory discovery app",
    version="1.0.0"
)

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(map.router, prefix="/v1/map", tags=["map"])
app.include_router(memories.router, prefix="/v1/memories", tags=["memories"])
app.include_router(social.router, prefix="/v1", tags=["social"])
app.include_router(places.router, prefix="/v1/places", tags=["places"])
app.include_router(discovery.router, prefix="/v1/discovery", tags=["discovery"])
app.include_router(media.router, prefix="/v1", tags=["media"])
app.include_router(profile.router, prefix="/v1/profile", tags=["profile"])
app.include_router(chat.router, prefix="/v1/conversations", tags=["chat"])
app.include_router(collections.router, prefix="/v1/collections", tags=["collections"])
app.include_router(reports.router, prefix="/v1/reports", tags=["reports"])
app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])

# Initialize Redis pub/sub for WebSocket cross-worker sync on each worker startup
@app.on_event("startup")
async def startup_event():
    await chat.manager.init_redis()
    redis = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0").replace("/0", "/1"),
        encoding="utf-8", decode_responses=True
    )
    await FastAPILimiter.init(redis)

from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware — block .env scanning, WordPress probes, credential file scanning
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path.lower()
    
    # Block .env file scanning
    if '.env' in path:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    # Block WordPress scanning
    if 'wp-admin' in path or 'wp-login' in path:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    # Block credential/key file scanning
    blocked_patterns = [
        'service-account.json', 'credentials.json', 'gcp-key', 'firebase',
        'google-key', 'keyfile.json', 'cloud-key', 'gcloud-service',
        'application_default_credentials'
    ]
    if any(bp in path for bp in blocked_patterns):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    return await call_next(request)

@app.get("/", response_class=HTMLResponse)
def read_root():
    file_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Waymark UI static file not found"

@app.get("/api-docs-manual", response_class=HTMLResponse)
def read_api_docs_manual():
    # Read api_documentation.md dynamically from workspace root
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api_documentation.md")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
    else:
        markdown_content = "# API Documentation\nTệp `api_documentation.md` không tìm thấy trong thư mục gốc."

    escaped_markdown = json.dumps(markdown_content)

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Waymark - API Manual Document</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Marked JS for Markdown parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    
    <!-- Prism JS for Syntax Highlighting -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>

    <style>
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            scroll-behavior: smooth;
        }}
        pre, code {{
            font-family: 'JetBrains Mono', monospace !important;
        }}
        /* Custom premium scrollbar */
        ::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        ::-webkit-scrollbar-track {{
            background: #0f0f16;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #2b2b3d;
            border-radius: 9999px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #cba6f7;
        }}
        /* Adapting style for premium dark markdown presentation */
        .markdown-body h1 {{
            font-size: 2rem;
            font-weight: 700;
            border-bottom: 2px solid #2b2b3d;
            padding-bottom: 0.75rem;
            margin-top: 2.5rem;
            margin-bottom: 1.25rem;
            color: #f5c2e7;
            background: linear-gradient(to right, #f5c2e7, #cba6f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .markdown-body h2 {{
            font-size: 1.5rem;
            font-weight: 600;
            border-bottom: 1px solid #2b2b3d;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            color: #cba6f7;
        }}
        .markdown-body h3 {{
            font-size: 1.15rem;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            color: #89b4fa;
        }}
        .markdown-body p {{
            margin-bottom: 1rem;
            line-height: 1.75;
            color: #cdd6f4;
        }}
        .markdown-body ul, .markdown-body ol {{
            margin-bottom: 1rem;
            padding-left: 1.5rem;
            color: #cdd6f4;
        }}
        .markdown-body ul {{
            list-style-type: disc;
        }}
        .markdown-body ol {{
            list-style-type: decimal;
        }}
        .markdown-body li {{
            margin-bottom: 0.35rem;
            line-height: 1.6;
        }}
        .markdown-body table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #2b2b3d;
        }}
        .markdown-body th, .markdown-body td {{
            padding: 0.85rem 1.15rem;
            text-align: left;
        }}
        .markdown-body th {{
            background-color: #181825;
            color: #cba6f7;
            font-weight: 600;
            border-bottom: 2px solid #2b2b3d;
        }}
        .markdown-body td {{
            background-color: #11111b;
            color: #bac2de;
            border-bottom: 1px solid #1e1e2e;
        }}
        .markdown-body tr:last-child td {{
            border-bottom: none;
        }}
        .markdown-body tr:nth-child(even) td {{
            background-color: #161624;
        }}
        .markdown-body blockquote {{
            border-left: 4px solid #cba6f7;
            padding-left: 1.25rem;
            color: #a6adc8;
            font-style: italic;
            margin: 1.5rem 0;
            background: #181825;
            padding-top: 0.75rem;
            padding-bottom: 0.75rem;
            border-radius: 0 8px 8px 0;
        }}
        .markdown-body code:not(pre code) {{
            background-color: #2b2b3d;
            color: #f5e0dc;
            padding: 0.15rem 0.35rem;
            border-radius: 6px;
            font-size: 0.9em;
        }}
        .markdown-body pre {{
            background-color: #181825 !important;
            border-radius: 12px;
            padding: 1.25rem;
            margin: 1.5rem 0;
            overflow-x: auto;
            border: 1px solid #2b2b3d;
            position: relative;
        }}
        .markdown-body a {{
            color: #89b4fa;
            text-decoration: none;
            transition: all 0.2s ease-in-out;
        }}
        .markdown-body a:hover {{
            color: #b4befe;
            text-decoration: underline;
        }}
    </style>
</head>
<body class="bg-[#0f0f16] text-[#cdd6f4] min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-[#11111b]/80 backdrop-blur-md border-b border-[#2b2b3d] sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 md:px-8 py-4 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="text-2xl font-bold bg-gradient-to-r from-[#f5c2e7] via-[#cba6f7] to-[#89b4fa] bg-clip-text text-transparent">Waymark</span>
                <span class="text-xs bg-[#2b2b3d] px-2.5 py-1 rounded-full text-[#a6adc8] font-medium border border-[#3c3c52]">API Manual Docs</span>
            </div>
            <div class="flex items-center space-x-3">
                <a href="/docs" class="text-xs md:text-sm bg-[#181825] border border-[#2b2b3d] hover:bg-[#2b2b3d] text-[#cdd6f4] font-medium px-4 py-2 rounded-lg transition-all duration-200">
                    Swagger UI (Interactive)
                </a>
                <a href="/redoc" class="text-xs md:text-sm bg-gradient-to-r from-[#cba6f7] to-[#89b4fa] hover:opacity-90 text-[#11111b] font-semibold px-4 py-2 rounded-lg shadow-lg shadow-indigo-500/10 transition-all duration-200">
                    ReDoc UI
                </a>
            </div>
        </div>
    </header>

    <!-- Main Content Container -->
    <div class="flex-grow max-w-7xl w-full mx-auto px-4 md:px-8 py-8 flex gap-8">
        <!-- Sidebar Menu -->
        <aside class="w-64 shrink-0 hidden lg:block sticky top-24 self-start max-h-[calc(100vh-8rem)] overflow-y-auto pr-4 border-r border-[#2b2b3d]/60">
            <div class="flex items-center justify-between mb-4">
                <h4 class="text-xs uppercase tracking-wider font-bold text-[#a6adc8]">Mục lục chi tiết</h4>
            </div>
            <ul id="toc-list" class="space-y-1 text-sm text-[#bac2de]">
                <!-- Populated dynamically via JS -->
            </ul>
        </aside>

        <!-- API Content Viewer -->
        <main class="flex-grow overflow-hidden">
            <div id="markdown-container" class="markdown-body bg-[#11111b] border border-[#2b2b3d] rounded-2xl p-6 md:p-10 shadow-2xl">
                <!-- Loading indicator -->
                <div class="flex flex-col items-center justify-center py-24 space-y-4">
                    <svg class="animate-spin h-10 w-10 text-[#cba6f7]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span class="text-sm text-[#a6adc8]">Đang hiển thị tài liệu hướng dẫn...</span>
                </div>
            </div>
        </main>
    </div>

    <!-- Footer -->
    <footer class="bg-[#11111b] border-t border-[#2b2b3d] py-6 text-center text-xs text-[#a6adc8]">
        <p>&copy; 2026 Waymark App. Hệ Thống Tài Liệu API Hướng Dẫn Tích Hợp.</p>
    </footer>

    <script>
        const rawMarkdown = {escaped_markdown};

        // Render Markdown safely on client
        marked.setOptions({{
            gfm: true,
            breaks: true,
            headerIds: true,
            headerPrefix: 'sec-',
            mangle: false
        }});

        const htmlContent = marked.parse(rawMarkdown);
        const container = document.getElementById('markdown-container');
        container.innerHTML = htmlContent;

        // Code highlight
        Prism.highlightAllUnder(container);

        // Populate Table of Contents
        const tocList = document.getElementById('toc-list');
        const headers = container.querySelectorAll('h1, h2');
        headers.forEach((header, index) => {{
            const text = header.textContent;
            const id = 'header-' + index;
            header.id = id;
            
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = '#' + id;
            a.textContent = text;
            
            if (header.tagName === 'H1') {{
                a.className = 'font-bold text-[#f5c2e7] hover:text-[#b4befe] block py-1.5 border-b border-[#2b2b3d]/40 mb-1 mt-3 first:mt-0 transition-colors duration-150';
            }} else {{
                a.className = 'pl-4 text-[#bac2de] hover:text-[#cba6f7] block py-1 text-xs border-l border-[#2b2b3d] hover:border-[#cba6f7] transition-all duration-150';
            }}
            
            li.appendChild(a);
            tocList.appendChild(li);
        }});

        // Add copy code buttons beautifully
        document.querySelectorAll('pre').forEach(pre => {{
            const btn = document.createElement('button');
            btn.className = 'absolute top-3 right-3 bg-[#2b2b3d] hover:bg-[#3c3c52] text-[#cdd6f4] border border-[#3c3c52] text-xs px-2.5 py-1 rounded-lg transition-all duration-200 shadow-md opacity-0 group-hover:opacity-100 focus:opacity-100';
            btn.innerHTML = 'Copy';
            pre.classList.add('group');
            pre.appendChild(btn);
            
            const codeEl = pre.querySelector('code');
            
            btn.addEventListener('click', () => {{
                const text = codeEl.textContent;
                navigator.clipboard.writeText(text).then(() => {{
                    btn.innerHTML = 'Copied!';
                    btn.classList.add('bg-green-600/20', 'text-green-400', 'border-green-600/40');
                    setTimeout(() => {{
                        btn.innerHTML = 'Copy';
                        btn.classList.remove('bg-green-600/20', 'text-green-400', 'border-green-600/40');
                    }}, 2000);
                }});
            }});
        }});
    </script>
</body>
</html>"""
    return html_content

@app.get("/v1/health")
def health_check(db: Session = Depends(get_db)):
    return {"status": "ok", "db_connected": db is not None}
