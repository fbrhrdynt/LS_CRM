"""LogiLicense tutorial PDF generation."""
import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
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
    KeepTogether,
)


BRAND_BLACK = colors.HexColor("#111111")
BRAND_BLUE = colors.HexColor("#002FA7")
BRAND_MUTED = colors.HexColor("#555555")
GREY_LIGHT = colors.HexColor("#F5F5F3")
GREY_BORDER = colors.HexColor("#D4D4D2")
CODE_BG = colors.HexColor("#0E1116")
CODE_FG = colors.HexColor("#E6E6E6")


def _styles():
    return {
        "H1": ParagraphStyle(name="H1", fontName="Helvetica-Bold", fontSize=26, leading=30, textColor=BRAND_BLACK, spaceAfter=6),
        "H2": ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=BRAND_BLACK, spaceBefore=12, spaceAfter=6),
        "H3": ParagraphStyle(name="H3", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=BRAND_BLUE, spaceBefore=8, spaceAfter=2),
        "Body": ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10, leading=14, textColor=BRAND_BLACK, spaceAfter=4, alignment=TA_LEFT),
        "Muted": ParagraphStyle(name="Muted", fontName="Helvetica", fontSize=9, leading=12, textColor=BRAND_MUTED),
        "Eyebrow": ParagraphStyle(name="Eyebrow", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=BRAND_MUTED),
        "CodeCaption": ParagraphStyle(name="CodeCaption", fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.white, backColor=BRAND_BLACK, borderPadding=(4, 6, 4, 6)),
    }


def _code_block(text: str):
    """Return a Preformatted block with dark-theme background."""
    style = ParagraphStyle(
        name="Code",
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=CODE_FG,
        backColor=CODE_BG,
        borderPadding=(8, 10, 8, 10),
        leftIndent=0,
        rightIndent=0,
    )
    return Preformatted(text, style)


def _page_decorator(canvas, doc, footer_text: str):
    canvas.saveState()
    # Header rule
    canvas.setStrokeColor(BRAND_BLACK)
    canvas.setLineWidth(1)
    canvas.line(18 * mm, A4[1] - 15 * mm, A4[0] - 18 * mm, A4[1] - 15 * mm)
    # Top brand
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(BRAND_BLACK)
    canvas.drawString(18 * mm, A4[1] - 12 * mm, "LOGISOURCE · LOGILICENSE")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 12 * mm, footer_text)
    # Footer
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawString(18 * mm, 10 * mm, "LogiLicense · Setup Guide")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _build_doc(footer_text: str):
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
        title="LogiLicense Setup Guide",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(
        id="page",
        frames=[frame],
        onPage=lambda c, d: _page_decorator(c, d, footer_text),
    )
    doc.addPageTemplates([template])
    return doc, buf


def build_logilicense_tutorial_pdf(settings: dict, base_url: str, license: dict | None = None) -> bytes:
    """Generate the LogiLicense setup guide. If `license` is provided, examples are
    personalised with its actual license_key + product_slug."""
    s = _styles()
    company = settings.get("company_name", "LogiSource Digital")
    tagline = settings.get("company_tagline", "Digital. Reliable. Connected.")
    footer_text = license["product_name"] if license else "Generic Setup Guide"
    doc, buf = _build_doc(footer_text)

    example_key = license["license_key"] if license else "LOGI-XXXX-XXXX-XXXX-XXXX"
    example_slug = (license or {}).get("product_slug", "") or "your-product"
    api_base = base_url.rstrip("/") + "/api/public/license"

    story = []

    # --- COVER ---
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("LogiLicense", s["Eyebrow"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Setup &amp; Integration Guide", s["H1"]))
    story.append(Paragraph(
        "Everything you need to issue a license key in LogiSource and enforce Pro / Premium "
        "features inside any external project — websites, APIs, mobile apps, or IoT devices.",
        s["Body"],
    ))
    story.append(Spacer(1, 12 * mm))

    if license:
        info_data = [
            ["Product", license["product_name"]],
            ["License Key", license["license_key"]],
            ["Plan", (license.get("plan") or "").upper()],
            ["Status", (license.get("status") or "").upper()],
            ["Max activations", str(license.get("max_activations") or "unlimited")],
            ["Expiry", license.get("expiry_date") or "Perpetual"],
        ]
    else:
        info_data = [
            ["Guide type", "Generic (no key personalisation)"],
            ["Public API base", api_base],
            ["Key format", "LOGI-XXXX-XXXX-XXXX-XXXX"],
        ]
    info = Table(info_data, colWidths=[45 * mm, 110 * mm])
    info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_MUTED),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), GREY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info)
    story.append(Spacer(1, 40 * mm))

    story.append(Paragraph(f"<b>{company}</b>", s["Body"]))
    story.append(Paragraph(tagline, s["Muted"]))
    story.append(Paragraph(datetime.now(timezone.utc).strftime("Generated %d %B %Y · %H:%M UTC"), s["Muted"]))

    story.append(PageBreak())

    # --- TOC ---
    story.append(Paragraph("Contents", s["H1"]))
    toc = [
        ["1", "How LogiLicense works"],
        ["2", "Generate a license (LogiSource admin)"],
        ["3", "Put the key inside your project"],
        ["4", "Verify the license from your project"],
        ["5", "Activate a device (per-machine limits)"],
        ["6", "Ready-to-use code snippets"],
        ["7", "Handling invalid / expired keys (Trial fallback)"],
        ["8", "Best practices"],
        ["9", "Full API reference"],
    ]
    tbl = Table(toc, colWidths=[12 * mm, 160 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_BLUE),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(PageBreak())

    # --- SECTION 1 ---
    story.append(Paragraph("1 · How LogiLicense works", s["H2"]))
    story.append(Paragraph(
        "LogiLicense turns LogiSource into an <b>online license authority</b>. Your other products — "
        "websites, APIs, IoT firmware, mobile apps, WordPress plugins — call a public HTTP endpoint "
        "with a license key. LogiSource replies with the plan, feature flags and expiry information, "
        "and your product unlocks Pro/Premium features accordingly. Invalid or missing keys always fall "
        'back to <b>plan: "trial"</b> so end users still get a working (but limited) experience.',
        s["Body"],
    ))
    story.append(Spacer(1, 4 * mm))

    flow_data = [
        ["1.", "Admin generates a license key inside LogiSource → LogiLicense."],
        ["2.", "Admin sends the key to the customer / embeds it in the product's environment."],
        ["3.", "On startup, the product calls POST /api/public/license/verify with the key + a device fingerprint."],
        ["4.", "LogiSource replies with valid:true / plan / features → product enables Pro."],
        ["5.", "If reply is valid:false → product runs in trial mode."],
        ["6.", "Every call is silently logged (IP, fingerprint, User-Agent, result)."],
    ]
    fl = Table(flow_data, colWidths=[10 * mm, 165 * mm])
    fl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(fl)

    # --- SECTION 2 ---
    story.append(Paragraph("2 · Generate a license (LogiSource admin)", s["H2"]))
    story.append(Paragraph("Step by step, inside the LogiSource web app:", s["Body"]))
    steps = [
        ["a.", "Log in as an admin at your LogiSource URL."],
        ["b.", "Open the sidebar → <b>Operations</b> → <b>LogiLicense</b>."],
        ["c.", "Click <b>Issue license</b> in the top-right corner."],
        ["d.", "Fill in the form:"],
        ["", "• <b>Product Name</b> — human name, e.g. \"MyIoT Dashboard\"."],
        ["", "• <b>Product Slug</b> — URL-safe id, e.g. \"myiot\". Used to guard the key against wrong products."],
        ["", "• <b>Plan</b> — trial / starter / pro / premium / enterprise / lifetime."],
        ["", "• <b>Feature flags</b> — comma-separated tokens your project checks (e.g. cloud_sync, unlimited_devices)."],
        ["", "• <b>Customer / Project</b> — optional linkage for reporting."],
        ["", "• <b>Max activations</b> — how many devices this key allows. 0 = unlimited."],
        ["", "• <b>Expiry Date</b> — leave empty for perpetual license."],
        ["e.", "Click <b>Issue license</b>. LogiSource returns a unique key like <font face='Courier'>LOGI-7SW2-RECF-VSBY-D7DN</font>."],
        ["f.", "Copy the key from the confirmation dialog or the list row. You can also open the license detail page for copy-paste-ready snippets."],
    ]
    st = Table([[a, Paragraph(b, s["Body"])] for a, b in steps], colWidths=[10 * mm, 165 * mm])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (0, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(st)

    # --- SECTION 3 ---
    story.append(PageBreak())
    story.append(Paragraph("3 · Put the key inside your project", s["H2"]))
    story.append(Paragraph(
        "Never hard-code license keys in source code. Use an <b>environment variable</b> so keys can be "
        "rotated without a code change. Below are three common places to store the key:",
        s["Body"],
    ))

    story.append(Paragraph(".env file (Node.js, Python, generic)", s["H3"]))
    story.append(_code_block(f"""# .env
LOGI_LICENSE_KEY={example_key}
LOGI_PRODUCT_SLUG={example_slug}
LOGI_API_BASE={api_base}"""))

    story.append(Paragraph("Docker / docker-compose", s["H3"]))
    story.append(_code_block(f"""# docker-compose.yml
services:
  myapp:
    image: myapp:latest
    environment:
      - LOGI_LICENSE_KEY={example_key}
      - LOGI_PRODUCT_SLUG={example_slug}
      - LOGI_API_BASE={api_base}"""))

    story.append(Paragraph("IoT / firmware — provisioning file", s["H3"]))
    story.append(_code_block(f"""// /etc/myproduct/license.conf  (mode 0600, root:root)
{{
  "license_key": "{example_key}",
  "product_slug": "{example_slug}",
  "api_base":    "{api_base}"
}}"""))

    # --- SECTION 4 ---
    story.append(PageBreak())
    story.append(Paragraph("4 · Verify the license from your project", s["H2"]))
    story.append(Paragraph(
        "On app startup call <b>POST /api/public/license/verify</b>. No authentication is required — "
        "the license key itself is the credential. Send the key, a stable per-device fingerprint, and "
        "optionally the product_slug to enforce it.",
        s["Body"],
    ))
    story.append(Paragraph("Request", s["H3"]))
    story.append(_code_block(f"""POST {api_base}/verify
Content-Type: application/json

{{
  "license_key":  "{example_key}",
  "fingerprint":  "device-uuid-here",
  "product_slug": "{example_slug}"
}}"""))
    story.append(Paragraph("Successful response", s["H3"]))
    story.append(_code_block("""HTTP/1.1 200 OK

{
  "valid": true,
  "product_name": "MyIoT Dashboard",
  "product_slug": "myiot",
  "plan":     "pro",
  "features": ["cloud_sync", "unlimited_devices"],
  "status":   "active",
  "expiry_date": "2027-12-31",
  "days_left":   533,
  "max_activations": 3,
  "activation_count": 1,
  "verified_at": "2026-07-15T17:40:45.048315+00:00"
}"""))

    story.append(Paragraph("Failure response (still HTTP 200 — never crashes)", s["H3"]))
    story.append(_code_block("""HTTP/1.1 200 OK

{
  "valid":   false,
  "reason":  "expired",           // invalid_key | revoked | suspended | expired | product_mismatch
  "message": "License has expired.",
  "plan":    "trial"
}"""))

    # --- SECTION 5 ---
    story.append(PageBreak())
    story.append(Paragraph("5 · Activate a device (per-machine limits)", s["H2"]))
    story.append(Paragraph(
        "If <b>Max activations</b> matters for your product (e.g. Pro allows only 3 machines), call "
        "<b>/activate</b> the first time each device runs. LogiSource keeps a table of unique fingerprints "
        "and rejects the (N+1)-th device with <b>reason: limit_reached</b>. Re-calling /activate with the same "
        "fingerprint is idempotent — it just refreshes last-seen.",
        s["Body"],
    ))
    story.append(_code_block(f"""POST {api_base}/activate
Content-Type: application/json

{{
  "license_key":  "{example_key}",
  "fingerprint":  "stable-device-id",
  "hostname":     "server-01.example.com"
}}"""))

    story.append(Paragraph("Recommended fingerprint sources", s["H3"]))
    fingerprint_data = [
        ["Node.js", "node-machine-id package or crypto.createHash('sha256').update(os.hostname()+process.platform).digest('hex')"],
        ["Python", "uuid.getnode() or hashlib.sha256((platform.node()+platform.machine()).encode()).hexdigest()"],
        ["Browser (SPA)", "FingerprintJS Pro, or crypto.randomUUID() persisted in localStorage"],
        ["IoT / Linux", "/etc/machine-id or MAC address of the primary NIC"],
        ["Docker", "Contents of /etc/machine-id from the host, mounted read-only"],
    ]
    ft = Table([[a, Paragraph(b, s["Muted"])] for a, b in fingerprint_data], colWidths=[35 * mm, 138 * mm])
    ft.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), GREY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(ft)

    story.append(Paragraph("Optional heartbeat (keeps last-seen fresh)", s["H3"]))
    story.append(_code_block(f"""POST {api_base}/heartbeat  (call every 15–60 minutes)
Content-Type: application/json

{{
  "license_key": "{example_key}",
  "fingerprint": "stable-device-id"
}}"""))

    # --- SECTION 6 : SNIPPETS ---
    story.append(PageBreak())
    story.append(Paragraph("6 · Ready-to-use code snippets", s["H2"]))

    story.append(Paragraph("Node.js (Express)", s["H3"]))
    story.append(_code_block(f"""// license.js — call once on startup, cache result in memory
const {{ machineIdSync }} = require("node-machine-id");

async function verifyLicense() {{
  try {{
    const res = await fetch("{api_base}/verify", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        license_key:  process.env.LOGI_LICENSE_KEY,
        fingerprint:  machineIdSync(),
        product_slug: process.env.LOGI_PRODUCT_SLUG,
      }}),
    }});
    return await res.json();
  }} catch (e) {{
    return {{ valid: false, plan: "trial" }};   // network fail → trial
  }}
}}

module.exports = async function initLicense(app) {{
  const info = await verifyLicense();
  app.locals.pro       = info.valid && info.plan !== "trial";
  app.locals.plan      = info.plan;
  app.locals.features  = new Set(info.features || []);
  console.log(app.locals.pro ? "✓ Pro unlocked" : "· Running in trial");
}};"""))

    story.append(Paragraph("Feature gating in a route", s["H3"]))
    story.append(_code_block("""app.post("/api/cloud-sync", (req, res) => {
  if (!req.app.locals.features.has("cloud_sync"))
    return res.status(402).json({ error: "Upgrade required" });
  // ... real cloud sync logic
});"""))

    story.append(Paragraph("Python", s["H3"]))
    story.append(_code_block(f"""# license.py
import os, uuid, requests

def verify_license():
    try:
        r = requests.post(
            "{api_base}/verify",
            json={{
                "license_key":  os.getenv("LOGI_LICENSE_KEY", ""),
                "fingerprint":  str(uuid.getnode()),
                "product_slug": os.getenv("LOGI_PRODUCT_SLUG", ""),
            }},
            timeout=5,
        )
        return r.json()
    except Exception:
        return {{"valid": False, "plan": "trial"}}

INFO      = verify_license()
IS_PRO    = INFO.get("valid") and INFO.get("plan") != "trial"
FEATURES  = set(INFO.get("features", []))

def require_feature(name: str):
    if name not in FEATURES:
        raise PermissionError(f"'{{name}}' requires Pro license")"""))

    story.append(Paragraph("PHP / WordPress plugin", s["H3"]))
    story.append(_code_block(f"""<?php
function my_verify_license() {{
    $body = json_encode([
        "license_key"  => get_option("logi_license_key"),
        "fingerprint"  => md5(gethostname() . PHP_OS),
        "product_slug" => "{example_slug}",
    ]);
    $ctx = stream_context_create([
        "http" => [
            "method"  => "POST",
            "header"  => "Content-Type: application/json",
            "content" => $body,
            "timeout" => 5,
        ],
    ]);
    $res = @file_get_contents("{api_base}/verify", false, $ctx);
    return $res ? json_decode($res, true) : ["valid" => false, "plan" => "trial"];
}}"""))

    story.append(Paragraph("cURL (test from your terminal)", s["H3"]))
    story.append(_code_block(f"""curl -X POST "{api_base}/verify" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "license_key":  "{example_key}",
    "fingerprint":  "test-device",
    "product_slug": "{example_slug}"
  }}'"""))

    # --- SECTION 7 ---
    story.append(PageBreak())
    story.append(Paragraph("7 · Handling invalid / expired keys (Trial fallback)", s["H2"]))
    story.append(Paragraph(
        "Every failure path returns a 200 OK response with <b>plan: \"trial\"</b>. Your client should "
        "treat this as \"downgrade to free tier\" without an exception. Recommended pattern:",
        s["Body"],
    ))
    story.append(_code_block("""const info = await verifyLicense();

if (info.valid && info.plan !== "trial") {
  // Pro — enable everything
  enableFeatures(info.features);
} else {
  // Trial — degrade gracefully
  hideFeature("cloud_sync");
  limit("devices", 1);
  showBanner(`Running in Trial (${info.reason || "no key"})`);
}"""))
    story.append(Paragraph("Reason codes you may see:", s["H3"]))
    reasons = [
        ("invalid_key", "The key was not found in LogiSource."),
        ("product_mismatch", "The key is for a different product_slug."),
        ("revoked", "The admin revoked the license."),
        ("suspended", "The admin temporarily suspended it."),
        ("expired", "expiry_date is in the past."),
        ("limit_reached", "This device is beyond the max_activations quota."),
    ]
    rt = Table([[a, b] for a, b in reasons], colWidths=[35 * mm, 140 * mm])
    rt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), GREY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(rt)

    # --- SECTION 8 ---
    story.append(Paragraph("8 · Best practices", s["H2"]))
    bp = [
        "Store the license key in an environment variable, never in git.",
        "Verify on startup, cache the result in memory. Re-verify daily via a background job.",
        "Use /heartbeat every 30–60 minutes if you care about accurate 'last seen' telemetry.",
        "Never bubble up a network error — always fall back to trial silently.",
        "Fingerprint should be stable across restarts. Random values will exhaust your activation quota.",
        "For SaaS product-slug enforcement, always send product_slug so a Pro key of Product A can't unlock Product B.",
        "Rotate keys instantly by clicking Revoke in LogiLicense — clients will fall back to trial on their next /verify.",
        "Wrap /verify with a 5-second timeout. Do not let license checks block user experience.",
    ]
    bpt = Table([["•", Paragraph(x, s["Body"])] for x in bp], colWidths=[6 * mm, 165 * mm])
    bpt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(bpt)

    # --- SECTION 9 ---
    story.append(PageBreak())
    story.append(Paragraph("9 · Full API reference", s["H2"]))
    endpoints = [
        ("POST", "/verify", "Check whether a key is valid. Returns plan/features/expiry. Always 200 OK."),
        ("POST", "/activate", "Register a device fingerprint. Idempotent per (key, fingerprint). Enforces max_activations."),
        ("POST", "/heartbeat", "Refresh last_seen for a registered device."),
        ("POST", "/deactivate", "Remove a device from the license activations table. Frees a slot."),
    ]
    story.append(Paragraph(f"Base URL &nbsp;&nbsp;<font face='Courier'>{api_base}</font>", s["Body"]))
    et = Table(
        [["Method", "Path", "Description"]] +
        [[m, p, d] for m, p, d in endpoints],
        colWidths=[20 * mm, 35 * mm, 120 * mm],
    )
    et.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (1, -1), "Courier-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
    ]))
    story.append(et)

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Common request headers", s["H3"]))
    story.append(_code_block("""Content-Type: application/json
User-Agent:   MyProduct/1.4.2 (linux; node)   # optional but logged"""))

    story.append(Paragraph("Rate limits", s["H3"]))
    story.append(Paragraph(
        "There is no hard rate limit today but every call is logged. Call /verify at startup and cache the result — "
        "do <b>not</b> call it on every request.",
        s["Muted"],
    ))

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        f"Need help? Open the license in LogiSource → LogiLicense → click <i>Integration</i>, or contact your LogiSource administrator.",
        s["Muted"],
    ))

    doc.build(story)
    return buf.getvalue()
