"""LogiSource Installation Guide PDF — how to run locally or deploy to hosting."""
import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Preformatted,
)


BRAND_BLACK = colors.HexColor("#111111")
BRAND_BLUE = colors.HexColor("#002FA7")
BRAND_MUTED = colors.HexColor("#555555")
GREY_LIGHT = colors.HexColor("#F5F5F3")
GREY_BORDER = colors.HexColor("#D4D4D2")
CODE_BG = colors.HexColor("#0E1116")
CODE_FG = colors.HexColor("#E6E6E6")
WARN_BG = colors.HexColor("#FFF4E0")
WARN_BORDER = colors.HexColor("#F5C86A")


def _styles():
    return {
        "H1": ParagraphStyle(name="H1", fontName="Helvetica-Bold", fontSize=26, leading=30, textColor=BRAND_BLACK, spaceAfter=6),
        "H2": ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=BRAND_BLACK, spaceBefore=14, spaceAfter=6),
        "H3": ParagraphStyle(name="H3", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=BRAND_BLUE, spaceBefore=10, spaceAfter=2),
        "H4": ParagraphStyle(name="H4", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=BRAND_BLACK, spaceBefore=8, spaceAfter=2),
        "Body": ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10, leading=14, textColor=BRAND_BLACK, spaceAfter=4, alignment=TA_LEFT),
        "Muted": ParagraphStyle(name="Muted", fontName="Helvetica", fontSize=9, leading=12, textColor=BRAND_MUTED),
        "Eyebrow": ParagraphStyle(name="Eyebrow", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=BRAND_MUTED),
        "Warn": ParagraphStyle(name="Warn", fontName="Helvetica", fontSize=9, leading=12, textColor=BRAND_BLACK, backColor=WARN_BG, borderColor=WARN_BORDER, borderPadding=(6, 8, 6, 8), borderWidth=0.6),
    }


def _code(text: str):
    style = ParagraphStyle(
        name="Code", fontName="Courier", fontSize=8, leading=10,
        textColor=CODE_FG, backColor=CODE_BG,
        borderPadding=(8, 10, 8, 10), leftIndent=0, rightIndent=0,
    )
    return Preformatted(text, style)


def _decorator(canvas, doc, footer_text: str):
    canvas.saveState()
    canvas.setStrokeColor(BRAND_BLACK)
    canvas.setLineWidth(1)
    canvas.line(18 * mm, A4[1] - 15 * mm, A4[0] - 18 * mm, A4[1] - 15 * mm)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(BRAND_BLACK)
    canvas.drawString(18 * mm, A4[1] - 12 * mm, "LOGISOURCE · INSTALLATION")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 12 * mm, footer_text)
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawString(18 * mm, 10 * mm, "LogiSource · Local & Hosting Setup")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _build_doc(footer_text: str):
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
        title="LogiSource Installation Guide",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=lambda c, d: _decorator(c, d, footer_text))])
    return doc, buf


def _row_table(rows, col_widths):
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), GREY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build_installation_pdf(settings: dict) -> bytes:
    s = _styles()
    company = settings.get("company_name", "LogiSource Digital")
    footer_text = "Installation & Deployment"
    doc, buf = _build_doc(footer_text)
    story = []

    # COVER
    story.append(Spacer(1, 22 * mm))
    story.append(Paragraph("Installation Guide", s["Eyebrow"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("LogiSource Integrated System", s["H1"]))
    story.append(Paragraph(
        "Complete step-by-step guide to install LogiSource on your local PC or deploy it to a "
        "production VPS / hosting. Covers Windows, macOS, Linux, plus optional Docker and static "
        "frontend hosting on Netlify / Vercel / S3.",
        s["Body"],
    ))
    story.append(Spacer(1, 14 * mm))
    stack = [
        ["Backend", "FastAPI 0.11x · Python 3.11+ · Motor (async MongoDB driver)"],
        ["Frontend", "React 19 · TailwindCSS · Shadcn UI · Craco"],
        ["Database", "MongoDB 5.0+"],
        ["Auth", "JWT (bcrypt) · AES-256-GCM vault"],
        ["Docs", "PDF via ReportLab · Excel via openpyxl"],
    ]
    story.append(_row_table(stack, [40 * mm, 130 * mm]))
    story.append(Spacer(1, 50 * mm))
    story.append(Paragraph(f"<b>{company}</b>", s["Body"]))
    story.append(Paragraph(datetime.now(timezone.utc).strftime("Generated %d %B %Y · %H:%M UTC"), s["Muted"]))

    story.append(PageBreak())

    # TOC
    story.append(Paragraph("Contents", s["H1"]))
    toc = [
        ["Part A", "Local PC installation"],
        ["1", "Pre-requirements (all platforms)"],
        ["2", "Install on Windows"],
        ["3", "Install on macOS"],
        ["4", "Install on Linux (Ubuntu / Debian)"],
        ["5", "First run &amp; login"],
        ["Part B", "Hosting / VPS deployment"],
        ["6", "Server requirements"],
        ["7", "Domain, DNS &amp; HTTPS"],
        ["8", "Full VPS setup (Ubuntu step-by-step)"],
        ["9", "nginx reverse proxy configuration"],
        ["10", "systemd service files"],
        ["11", "Docker deployment (optional)"],
        ["12", "Static frontend on Netlify / Vercel / S3"],
        ["Part C", "Operations"],
        ["13", "Environment variables reference"],
        ["14", "Backups &amp; disaster recovery"],
        ["15", "Troubleshooting"],
    ]
    body_style = ParagraphStyle(name="TocBody", fontName="Helvetica", fontSize=10, leading=12, textColor=BRAND_BLACK)
    label_style = ParagraphStyle(name="TocLabel", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=BRAND_BLUE)
    rows = [[Paragraph(a, label_style), Paragraph(b, body_style)] for a, b in toc]
    tbl = Table(rows, colWidths=[22 * mm, 150 * mm])
    tbl.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tbl)

    # ==================================================================
    # PART A — LOCAL PC
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("Part A · Local PC installation", s["H1"]))
    story.append(Paragraph(
        "This part gets LogiSource running on a developer's laptop or a single office PC. "
        "You'll extract the ZIP you downloaded from Website Settings → Download ZIP, install "
        "three dependencies (Python, Node.js and MongoDB), then start the backend and frontend "
        "as two separate processes.",
        s["Body"],
    ))

    # 1. PRE-REQUIREMENTS
    story.append(Paragraph("1 · Pre-requirements (all platforms)", s["H2"]))
    pre = [
        ["Tool", "Version", "Purpose"],
        ["Python", ">= 3.11", "Runs the FastAPI backend"],
        ["pip", "bundled with Python", "Installs backend Python packages"],
        ["Node.js", ">= 18.x (LTS)", "Runs the React frontend build"],
        ["Yarn", ">= 1.22", "Package manager for the frontend (npm is NOT supported)"],
        ["MongoDB", ">= 5.0", "Database (Community edition is fine)"],
        ["mongodump/mongorestore", "any recent", "For backup / restore of BSON dumps"],
        ["git", "any recent", "Optional — only if you plan to push code to a repo"],
    ]
    pt = Table(pre, colWidths=[40 * mm, 32 * mm, 100 * mm])
    pt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
    ]))
    story.append(pt)

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Recommended hardware", s["H3"]))
    story.append(Paragraph(
        "2 CPU cores · 4 GB RAM · 5 GB free disk. LogiSource itself is lightweight — "
        "most memory is spent on MongoDB (~500 MB idle) and the React dev server (~500 MB).",
        s["Body"],
    ))
    story.append(Paragraph(
        "⚠  Do <b>not</b> use <font face='Courier'>npm install</font> for the frontend. This project uses Yarn (see <font face='Courier'>yarn.lock</font>).",
        s["Warn"],
    ))

    # 2. WINDOWS
    story.append(PageBreak())
    story.append(Paragraph("2 · Install on Windows", s["H2"]))

    story.append(Paragraph("2.1  Install Python 3.11+", s["H3"]))
    story.append(Paragraph(
        "Download the installer from python.org/downloads. In the installer, tick "
        "<b>“Add python.exe to PATH”</b> before clicking Install. Verify:",
        s["Body"],
    ))
    story.append(_code("python --version\npip --version"))

    story.append(Paragraph("2.2  Install Node.js LTS + Yarn", s["H3"]))
    story.append(Paragraph(
        "Download the LTS installer from nodejs.org. After installation, open a new "
        "PowerShell as Administrator and enable Yarn via Corepack:",
        s["Body"],
    ))
    story.append(_code("corepack enable\ncorepack prepare yarn@stable --activate\nyarn --version"))

    story.append(Paragraph("2.3  Install MongoDB Community", s["H3"]))
    story.append(Paragraph(
        "Download MongoDB Community Server from mongodb.com/try/download/community. "
        "During install pick <b>“Complete”</b> and keep <b>“Install MongoDB as a Service”</b> ticked. "
        "MongoDB will run as a Windows Service on port 27017. Verify with MongoDB Compass or:",
        s["Body"],
    ))
    story.append(_code("\"C:\\Program Files\\MongoDB\\Server\\7.0\\bin\\mongosh.exe\" --eval \"db.runCommand({ping:1})\""))

    story.append(Paragraph("2.4  Extract the ZIP and set up the backend", s["H3"]))
    story.append(_code(r"""cd C:\LogiSource
Expand-Archive .\logisource-full-*.zip .   # or right-click → Extract All

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Restore the database (BSON dump)
mongorestore --uri "mongodb://localhost:27017" --db test_database ..\database\test_database

# Start the backend
uvicorn server:app --host 0.0.0.0 --port 8001"""))

    story.append(Paragraph("2.5  Start the frontend", s["H3"]))
    story.append(Paragraph("Open a second PowerShell window:", s["Body"]))
    story.append(_code(r"""cd C:\LogiSource\frontend
yarn install         # once, first time only
yarn start           # opens http://localhost:3000"""))

    # 3. macOS
    story.append(PageBreak())
    story.append(Paragraph("3 · Install on macOS", s["H2"]))
    story.append(Paragraph("The easiest path is Homebrew.", s["Body"]))
    story.append(Paragraph("3.1  Install Homebrew (if you don't have it)", s["H3"]))
    story.append(_code("/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""))
    story.append(Paragraph("3.2  Install runtimes", s["H3"]))
    story.append(_code("""brew install python@3.11 node yarn
brew tap mongodb/brew
brew install mongodb-community@7.0 mongodb-database-tools

# Start MongoDB as a background service
brew services start mongodb-community@7.0"""))
    story.append(Paragraph("3.3  Backend + frontend", s["H3"]))
    story.append(_code("""cd ~/Downloads && unzip logisource-full-*.zip -d ~/LogiSource
cd ~/LogiSource/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mongorestore --uri "mongodb://localhost:27017" --db test_database ../database/test_database
uvicorn server:app --host 0.0.0.0 --port 8001 &

cd ../frontend
yarn install && yarn start"""))

    # 4. LINUX
    story.append(Paragraph("4 · Install on Linux (Ubuntu 22.04 / Debian 12)", s["H2"]))
    story.append(Paragraph("4.1  Install runtimes", s["H3"]))
    story.append(_code("""sudo apt update && sudo apt install -y python3-venv python3-pip curl git

# Node.js 20 LTS + Yarn via Corepack
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo corepack enable

# MongoDB 7 (Ubuntu 22.04)
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \\
    sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \\
    sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod"""))
    story.append(Paragraph("4.2  Extract and run", s["H3"]))
    story.append(_code("""unzip logisource-full-*.zip -d ~/LogiSource
cd ~/LogiSource/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mongorestore --uri "mongodb://localhost:27017" --db test_database ../database/test_database
uvicorn server:app --host 0.0.0.0 --port 8001 &

cd ../frontend
yarn install && yarn start"""))

    # 5. First run
    story.append(Paragraph("5 · First run &amp; login", s["H2"]))
    story.append(Paragraph(
        "With backend on <font face='Courier'>:8001</font> and frontend on <font face='Courier'>:3000</font>, open "
        "http://localhost:3000 in your browser. Log in with the seed credentials:",
        s["Body"],
    ))
    creds = [
        ["Administrator", "admin@logisource.com", "Admin@12345"],
        ["Staff", "staff@logisource.com", "Staff@12345"],
    ]
    story.append(_row_table([["Role", "Email", "Password"]] + creds, [45 * mm, 70 * mm, 55 * mm]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "⚠  Immediately change both passwords from the top-right menu → <b>Change Password</b>, "
        "and open Website Settings to configure your company name, tax %, and prefixes.",
        s["Warn"],
    ))

    # ==================================================================
    # PART B — HOSTING
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("Part B · Hosting / VPS deployment", s["H1"]))
    story.append(Paragraph(
        "This part covers a real production deployment on a Linux VPS with a domain, "
        "HTTPS via Let's Encrypt, and process management via systemd.",
        s["Body"],
    ))

    # 6. Server requirements
    story.append(Paragraph("6 · Server requirements", s["H2"]))
    hw = [
        ["Component", "Minimum", "Recommended"],
        ["CPU", "1 vCPU", "2 vCPU"],
        ["RAM", "2 GB", "4 GB"],
        ["Disk", "10 GB SSD", "20 GB SSD"],
        ["OS", "Ubuntu 22.04 LTS", "Ubuntu 22.04 LTS"],
        ["Network", "Public IPv4", "Public IPv4 + IPv6"],
        ["Ports open", "80, 443 (public); 8001 &amp; 27017 loopback only", ""],
    ]
    hwt = Table(hw, colWidths=[40 * mm, 62 * mm, 68 * mm])
    hwt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
    ]))
    story.append(hwt)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Popular VPS providers: DigitalOcean ($6/mo droplet), Hetzner (€4/mo CX22), Vultr, Linode, or any on-prem server.",
        s["Muted"],
    ))

    # 7. Domain
    story.append(Paragraph("7 · Domain, DNS &amp; HTTPS", s["H2"]))
    story.append(Paragraph(
        "Point one subdomain (e.g. <b>logisource.yourdomain.com</b>) to the server's public IP with "
        "an A record. Optionally use a second subdomain for the backend API "
        "(e.g. <b>api.logisource.yourdomain.com</b>) — but a single subdomain with an "
        "nginx reverse-proxy for both <font face='Courier'>/</font> (frontend) and <font face='Courier'>/api/</font> (backend) is simpler.",
        s["Body"],
    ))
    story.append(Paragraph(
        "HTTPS is mandatory in production because the JWT auth cookie has <font face='Courier'>Secure</font> flag on. "
        "Use certbot for a free Let's Encrypt certificate (installed in section 8).",
        s["Body"],
    ))

    # 8. Full VPS setup
    story.append(PageBreak())
    story.append(Paragraph("8 · Full VPS setup (Ubuntu 22.04 step-by-step)", s["H2"]))
    story.append(Paragraph("SSH into the fresh server as root, then:", s["Body"]))
    story.append(Paragraph("8.1  Base hardening &amp; users", s["H3"]))
    story.append(_code("""adduser deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
# Now log in as deploy@server and continue

sudo apt update && sudo apt upgrade -y
sudo apt install -y ufw
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443
sudo ufw --force enable"""))
    story.append(Paragraph("8.2  Install runtimes (same as Section 4.1)", s["H3"]))
    story.append(Paragraph("Repeat the Ubuntu install script from section 4.1 (Python, Node, Yarn, MongoDB).", s["Body"]))

    story.append(Paragraph("8.3  Upload &amp; extract LogiSource", s["H3"]))
    story.append(_code("""sudo mkdir -p /opt/logisource && sudo chown deploy:deploy /opt/logisource
cd /opt/logisource
# Upload logisource-full-*.zip via scp/sftp, then:
unzip logisource-full-*.zip
ls   # should show backend/ frontend/ database/ memory/ README.md"""))

    story.append(Paragraph("8.4  Rotate secrets (mandatory!)", s["H3"]))
    story.append(_code(r"""cd /opt/logisource/backend

# Generate strong values
python3 -c "import secrets; print('JWT_SECRET='+secrets.token_hex(32))"
python3 -c "import secrets; print('VAULT_MASTER_KEY='+secrets.token_hex(32))"

# Edit .env — REPLACE JWT_SECRET, VAULT_MASTER_KEY, ADMIN_PASSWORD, STAFF_PASSWORD
nano .env"""))
    story.append(Paragraph(
        "⚠  If you rotate VAULT_MASTER_KEY on an existing database, all encrypted vault passwords "
        "become unreadable. Rotate BEFORE users add credentials, or plan a decrypt-re-encrypt migration.",
        s["Warn"],
    ))

    story.append(Paragraph("8.5  Restore database", s["H3"]))
    story.append(_code("""cd /opt/logisource/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

mongorestore --uri "mongodb://localhost:27017" --db test_database \\
  ../database/test_database"""))

    story.append(Paragraph("8.6  Build the frontend for production", s["H3"]))
    story.append(_code("""cd /opt/logisource/frontend

# Point the compiled bundle at your public backend URL
echo "REACT_APP_BACKEND_URL=https://logisource.yourdomain.com" > .env

yarn install
yarn build     # output → /opt/logisource/frontend/build/"""))

    # 9. nginx
    story.append(PageBreak())
    story.append(Paragraph("9 · nginx reverse proxy", s["H2"]))
    story.append(_code("""sudo apt install -y nginx certbot python3-certbot-nginx"""))
    story.append(Paragraph("Create <font face='Courier'>/etc/nginx/sites-available/logisource</font>:", s["Body"]))
    story.append(_code("""server {
    listen 80;
    server_name logisource.yourdomain.com;

    # ---- Frontend (static build) ----
    root /opt/logisource/frontend/build;
    index index.html;
    location / {
        try_files $uri /index.html;
    }

    # ---- Backend API ----
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout                 300s;
        client_max_body_size               50m;
    }
}"""))
    story.append(_code("""sudo ln -s /etc/nginx/sites-available/logisource /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Automatic HTTPS via Let's Encrypt
sudo certbot --nginx -d logisource.yourdomain.com --redirect --agree-tos -m you@yourdomain.com"""))
    story.append(Paragraph(
        "certbot will rewrite the nginx config to listen on 443 with a valid TLS certificate and "
        "auto-renew via a systemd timer. Test https://logisource.yourdomain.com in your browser.",
        s["Body"],
    ))

    # 10. systemd
    story.append(Paragraph("10 · systemd service for the backend", s["H2"]))
    story.append(Paragraph("Create <font face='Courier'>/etc/systemd/system/logisource-backend.service</font>:", s["Body"]))
    story.append(_code("""[Unit]
Description=LogiSource FastAPI backend
After=network.target mongod.service
Requires=mongod.service

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/opt/logisource/backend
Environment="PATH=/opt/logisource/backend/.venv/bin"
EnvironmentFile=/opt/logisource/backend/.env
ExecStart=/opt/logisource/backend/.venv/bin/uvicorn server:app \\
    --host 127.0.0.1 --port 8001 --workers 2 --proxy-headers
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target"""))
    story.append(_code("""sudo systemctl daemon-reload
sudo systemctl enable --now logisource-backend
sudo systemctl status logisource-backend
journalctl -u logisource-backend -f          # live logs"""))

    # 11. Docker
    story.append(PageBreak())
    story.append(Paragraph("11 · Docker deployment (optional)", s["H2"]))
    story.append(Paragraph(
        "If you prefer containers, drop this <font face='Courier'>docker-compose.yml</font> into the extracted folder "
        "next to <font face='Courier'>backend/</font> and <font face='Courier'>frontend/</font>:",
        s["Body"],
    ))
    story.append(_code("""services:
  mongo:
    image: mongo:7
    restart: unless-stopped
    volumes:
      - mongo-data:/data/db

  backend:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./backend:/app
    command: >
      sh -c "pip install -r requirements.txt &&
             uvicorn server:app --host 0.0.0.0 --port 8001 --workers 2"
    env_file: ./backend/.env
    environment:
      MONGO_URL: mongodb://mongo:27017
    depends_on: [mongo]
    ports: ["8001:8001"]

  frontend:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app
    command: sh -c "corepack enable && yarn install && yarn start"
    environment:
      REACT_APP_BACKEND_URL: http://localhost:8001
    ports: ["3000:3000"]

volumes:
  mongo-data:"""))
    story.append(_code("docker compose up -d\ndocker compose logs -f backend"))

    # 12. Static hosting
    story.append(Paragraph("12 · Static frontend on Netlify / Vercel / S3", s["H2"]))
    story.append(Paragraph(
        "The compiled <font face='Courier'>frontend/build/</font> folder is a plain static site. You can deploy the backend "
        "wherever (Render, Railway, self-hosted VPS) and host the frontend for free on a CDN.",
        s["Body"],
    ))
    story.append(Paragraph("Netlify", s["H3"]))
    story.append(_code("""# Once, on your machine
npm i -g netlify-cli   # (netlify's own tool; still uses your yarn build)
cd frontend && yarn build
netlify deploy --prod --dir=build"""))
    story.append(Paragraph("Vercel", s["H3"]))
    story.append(_code("""npm i -g vercel
cd frontend && vercel --prod
# In the Vercel dashboard, set env var: REACT_APP_BACKEND_URL"""))
    story.append(Paragraph("AWS S3 + CloudFront", s["H3"]))
    story.append(_code("""aws s3 sync frontend/build/ s3://your-bucket/ --delete
aws cloudfront create-invalidation --distribution-id ABCD --paths '/*'"""))
    story.append(Paragraph(
        "⚠  Whichever host you pick, remember to update <b>CORS_ORIGINS</b> in the backend .env "
        "to include the frontend's URL, or CORS-preflight requests will fail.",
        s["Warn"],
    ))

    # ==================================================================
    # PART C — OPERATIONS
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("Part C · Operations", s["H1"]))

    # 13. ENV
    story.append(Paragraph("13 · Environment variables reference", s["H2"]))
    envs = [
        ["Variable", "Where", "Purpose"],
        ["MONGO_URL", "backend/.env", "mongodb://user:pass@host:27017"],
        ["DB_NAME", "backend/.env", "Database name (default test_database — rename in prod!)"],
        ["JWT_SECRET", "backend/.env", "Signs auth tokens. 64 hex chars. ROTATE for prod."],
        ["JWT_ALGORITHM", "backend/.env", "HS256 (do not change)"],
        ["JWT_ACCESS_MINUTES", "backend/.env", "Token lifetime (default 720 = 12 hrs)"],
        ["VAULT_MASTER_KEY", "backend/.env", "AES-256 key for the credential vault. ROTATE ONCE at setup."],
        ["ADMIN_EMAIL / _PASSWORD", "backend/.env", "Seeded on first start-up if user doesn't exist"],
        ["STAFF_EMAIL / _PASSWORD", "backend/.env", "Same, for the seeded staff user"],
        ["CORS_ORIGINS", "backend/.env", "Comma-separated list, e.g. https://logisource.yourdomain.com"],
        ["COMPANY_NAME / _TAGLINE / _LOGO_URL", "backend/.env", "Default settings, editable in-app"],
        ["REACT_APP_BACKEND_URL", "frontend/.env", "Baked into the build. Set BEFORE running yarn build."],
    ]
    et = Table(envs, colWidths=[50 * mm, 30 * mm, 90 * mm])
    et.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (0, -1), "Courier-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
    ]))
    story.append(et)

    # 14. Backups
    story.append(Paragraph("14 · Backups &amp; disaster recovery", s["H2"]))
    story.append(Paragraph(
        "Two built-in backup paths — both accessible from Website Settings → Backup &amp; Restore:",
        s["Body"],
    ))
    story.append(Paragraph("• <b>Backup</b> — one-click JSON dump of every collection (small, portable, but not indexed).", s["Body"]))
    story.append(Paragraph("• <b>Download ZIP</b> — full source + BSON MongoDB dump. Use for archival + off-server storage.", s["Body"]))
    story.append(Paragraph("For scheduled off-server backups on a VPS, use this cron entry:", s["Body"]))
    story.append(_code("""# /etc/cron.d/logisource-backup
0 3 * * * deploy mongodump --uri "mongodb://localhost:27017" --db test_database \\
  --gzip --archive=/var/backups/logisource-$(date +\\%Y\\%m\\%d).gz"""))
    story.append(Paragraph("To restore any dump on a fresh install:", s["Body"]))
    story.append(_code("""mongorestore --uri "mongodb://localhost:27017" --gzip \\
  --archive=/var/backups/logisource-20260715.gz --nsInclude "test_database.*" """))

    # 15. Troubleshooting
    story.append(Paragraph("15 · Troubleshooting", s["H2"]))
    trouble = [
        ["Symptom", "Cause / Fix"],
        ["Login page loads but login POST returns 500", "backend not running or MONGO_URL unreachable. Check `journalctl -u logisource-backend -f`."],
        ["Login returns 401 with correct password", "JWT_SECRET was rotated after the token was issued. Log out (or clear localStorage) and log in again."],
        ["Vault reveal shows blank string", "VAULT_MASTER_KEY was changed after the record was created. Restore original key or re-enter credentials."],
        ["CORS error in browser console", "backend .env → CORS_ORIGINS must include the frontend URL (protocol + host, no trailing slash)."],
        ["yarn install fails with ENOENT node-gyp", "You are on npm. Delete node_modules + package-lock.json, then use `yarn install`."],
        ["nginx: 502 Bad Gateway on /api", "Backend process died. `sudo systemctl restart logisource-backend`."],
        ["Slow PDF generation on VPS", "Give the backend at least 512 MB RAM. Reduce uvicorn --workers to 1 on tiny droplets."],
        ["Cookie not set / user logs out immediately", "Frontend served over HTTP but backend cookie has Secure=true. Enforce HTTPS via certbot."],
    ]
    tt = Table(trouble, colWidths=[70 * mm, 100 * mm])
    tt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
    ]))
    story.append(tt)

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "Need more help? Open the LogiSource web app → sidebar → <b>Activity Logs</b> to see every "
        "backend action with timestamp and user, or open your VPS logs via <font face='Courier'>journalctl -u logisource-backend</font>.",
        s["Muted"],
    ))

    doc.build(story)
    return buf.getvalue()
