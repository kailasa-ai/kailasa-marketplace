#!/usr/bin/env python3
"""Send tagged email variants to seed inboxes to test Gmail tab placement (Primary vs Promotions).

Each variant is an .html file whose <title> is the subject; a same-stem .txt file, if present, is
the plain-text part (otherwise one is derived from the HTML). Subjects are tagged
[PT<round>-<letter>] in the order given, sends are spaced out, and each send is appended to a TSV
log. Afterwards, search the seed inbox for `subject:PT<round> category:primary` and
`category:promotions`.

The credentials file holds KEY=VALUE (or KEY: VALUE) lines: SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
SMTP_PASSWORD, SMTP_FROM_EMAIL, optional SMTP_FROM_NAME and SMTP_TLS (starttls | ssl | none).
It is read, never printed. SMTP_PASSWORD in the environment overrides the file.

Example:
  placement_test.py --creds ../mailer_creds.txt --to seed1@gmail.com --to seed2@gmail.com \\
      --round 3 --unsub-mailto contact@example.org control.html no_pitch.html
"""
import argparse
import ast
import os
import re
import smtplib
import ssl
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid, parseaddr
from html import unescape
from pathlib import Path


def load_creds(path):
    config = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        try:
            config[key] = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            config[key] = value
    config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD", config.get("SMTP_PASSWORD"))
    missing = [k for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL")
               if not config.get(k)]
    if missing:
        sys.exit(f"credentials file is missing: {', '.join(missing)}")
    return config


def html_to_text(html):
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S | re.I)
    body = body.group(1) if body else html
    body = re.sub(r"<(style|script|title)\b.*?</\1>", "", body, flags=re.S | re.I)
    body = re.sub(r'<div[^>]*display:\s*none[^>]*>.*?</div>', "", body, flags=re.S | re.I)  # preheader
    body = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"\2: \1", body, flags=re.S | re.I)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"</(p|div|blockquote|h[1-6]|li|tr|table)>|<hr[^>]*>", "\n\n", body, flags=re.I)
    text = unescape(re.sub(r"<[^>]+>", "", body))
    text = "\n".join(line.strip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def load_variant(path):
    path = Path(path)
    html = path.read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if not title:
        sys.exit(f"{path}: add a <title> with the subject line")
    txt = path.with_suffix(".txt")
    text = txt.read_text(encoding="utf-8") if txt.exists() else html_to_text(html)
    return unescape(title.group(1).strip()), text, html


def build_message(args, tag, subject, text, html, from_header, from_address, to):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{tag}] {subject}"
    msg["From"] = from_header
    msg["To"] = to
    if args.reply_to:
        msg["Reply-To"] = args.reply_to
    unsub = []
    if args.unsub_url:
        unsub.append(f"<{args.unsub_url}>")
    if args.unsub_mailto:
        unsub.append(f"<mailto:{args.unsub_mailto}?subject=unsubscribe>")
    if unsub:
        msg["List-Unsubscribe"] = ", ".join(unsub)
    if args.unsub_url:
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg["Message-ID"] = make_msgid(domain=from_address.split("@")[1])
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def connect(config):
    host, port = config["SMTP_HOST"], int(config["SMTP_PORT"])
    tls = str(config.get("SMTP_TLS", "starttls")).lower()
    if tls == "ssl":
        server = smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.ehlo()
        if tls == "starttls":
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
    server.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("variants", nargs="+", help="variant .html files, in send order (A, B, C, ...)")
    parser.add_argument("--creds", required=True, help="SMTP credentials file (never printed)")
    parser.add_argument("--to", action="append", required=True, help="seed inbox; repeat for several")
    parser.add_argument("--round", required=True, help="round id used in the [PT<round>-X] tag")
    parser.add_argument("--reply-to")
    parser.add_argument("--unsub-mailto", help="address for a mailto List-Unsubscribe entry")
    parser.add_argument("--unsub-url", help="https one-click unsubscribe URL (adds List-Unsubscribe-Post)")
    parser.add_argument("--gap", type=int, default=20, help="seconds between sends (default 20)")
    parser.add_argument("--log", default="placement_test_log.tsv")
    parser.add_argument("--dry-run", action="store_true", help="print subjects and text parts; send nothing")
    args = parser.parse_args()

    variants = [(f"PT{args.round}-{chr(65 + i)}", Path(v).stem, *load_variant(v)) for i, v in enumerate(args.variants)]
    if args.dry_run:
        for tag, name, subject, text, _ in variants:
            print(f"=== [{tag}] {subject}  ({name})\n{text}")
        return

    config = load_creds(args.creds)
    configured_name, from_address = parseaddr(config["SMTP_FROM_EMAIL"])
    from_address = from_address or config["SMTP_FROM_EMAIL"].strip()
    # Postal rejects apostrophes in display names.
    display_name = (config.get("SMTP_FROM_NAME") or configured_name).replace("'", "")
    from_header = formataddr((display_name, from_address))

    with connect(config) as server, open(args.log, "a", encoding="utf-8") as log:
        for n, (tag, name, subject, text, html) in enumerate(variants):
            for to in args.to:
                msg = build_message(args, tag, subject, text, html, from_header, from_address, to)
                server.sendmail(from_address, [to], msg.as_string())
                log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{tag}\t{name}\t{to}\t{msg['Subject']}\n")
                log.flush()
            print(f"sent {tag} {name} to {len(args.to)} inbox(es): {msg['Subject']}")
            if n < len(variants) - 1:
                time.sleep(args.gap)


if __name__ == "__main__":
    main()
