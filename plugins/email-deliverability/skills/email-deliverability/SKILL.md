---
name: email-deliverability
description: "Use when sending or preparing a bulk or campaign email (newsletters, reconnect or promo campaigns, event follow-ups), especially through Kailasa Mailer / Postal, or when asked why emails land in Gmail's Promotions tab instead of Primary, how to reach Primary, how to test inbox placement with seed inboxes, or what Google's bulk-sender rules (one-click unsubscribe, SPF/DKIM/DMARC) require. Covers the send checklist, the copy signals that move Gmail tab placement, and a script for running placement tests."
---

# Email deliverability and Gmail tab placement

This is what KAILASA learned from sending campaigns to tens of thousands of past participants,
including a 14-round, ~75-email Gmail placement study (Sept 2026). Use it so the next campaign
doesn't rediscover it.

Full study results: `references/placement-study.md`. Test script: `scripts/placement_test.py`.

## 1. Send checklist

1. **Use a real relay, not Gmail SMTP.** Gmail SMTP caps at ~2,000/day and errored 8,408 times on
   an August 2026 promo. Send through Kailasa Mailer (Postal, STARTTLS on port 25) with an
   authenticated `mail.<domain>` sending subdomain.
2. **Credentials stay in a file read by code only.** Never print, echo, log or paste them.
3. **Headers to set yourself:** `Message-ID` (`email.utils.make_msgid(domain=<sending domain>)`),
   `Date` (`formatdate(localtime=True)`), `From` with a display name (Postal rejects apostrophes
   in display names), and `Reply-To` pointing to a monitored inbox.
4. **Authentication:** SPF, DKIM and DMARC must all pass for the From domain.
   - Exactly **one** SPF TXT record per domain. A second one is a PermError, which means SPF fails.
     Merge `include:`s into a single record.
   - Check a received test's `Authentication-Results` header for `spf=pass dkim=pass dmarc=pass`.
5. **Google bulk-sender rules** (over 5,000 messages a day to Gmail addresses; see
   support.google.com/a/answer/81126 and /14229414):
   - One-click unsubscribe headers: `List-Unsubscribe: <https://…>` **and**
     `List-Unsubscribe-Post: List-Unsubscribe=One-Click`. A `mailto:`-only header does **not**
     count as one-click. You need an https endpoint that unsubscribes on POST without a login.
   - A visible unsubscribe link or instruction in the body.
   - Spam complaint rate under 0.3% (aim for under 0.1%).
   - Honour unsubscribes within 2 days. If people unsubscribe by replying, suppress those
     addresses before every send.
6. **List hygiene before a big send:** dedupe, and remove opt-outs, hard bounces, do-not-mail,
   non-marketable and spam-report contacts. Record why each one was dropped. Warm up a cold list:
   start at 5–10k a day and raise it only while bounces stay under 2% and complaints under 0.1%.
7. **Test before sending:** send yourself a test, check authentication, the rendering and the
   Gmail tab (section 3).

## 2. What decides Primary vs Promotions (Gmail)

These are findings from one Google Workspace seed inbox. Treat them as strong signals, not laws.

- **The body text decides.** The study ruled out the subject line, sender, link domain, UTM tags,
  Message-ID and Date, button style (table vs inline vs text link), blockquotes, preheader and
  HTML vs plain text. Swapping bodies between a Primary email and a Promotions email moved the
  tab with the body every time.
- **Gmail scores the whole email; signals add up.** No single phrase flips it. Removing any one
  paragraph from a Promotions email didn't help. Adding any one product paragraph to a Primary
  email didn't hurt, but all four together did.
- **These push toward Promotions:**
  - Product-introduction or pitch lines: "It's called X", "World's First AI for…", "we think
    you'll love it", feature lists, "your first answer takes seconds".
  - CTA framing such as "What's been on your mind lately? Sounds like you already have a place
    to start."
  - The `List-Unsubscribe` header **and** a visible unsubscribe footer. Each adds weight, and you
    can't drop either for a bulk send.
- **Borderline:** "It's been a long time since we were in touch" reconnect copy. It landed in
  Primary without unsubscribe signals and in Promotions with them, even with no product, link or
  button.
- **Stayed in Primary even with both unsubscribe signals and a CTA button:** a genuine community
  update to people who had just taken part in an event. It thanked them for joining a
  livestream, used "we / let us", had a long sadhana teaching section, and ended with one button.
  Copying that *style* in a new email for a long-unengaged audience still landed in Promotions,
  so the style alone is not a recipe.
- **What actually earns Primary is recipient engagement.** Gmail learns per recipient. Replies,
  moving an email to Primary and adding the sender to contacts carry over to later emails. Ask
  for replies (a "just hit reply, we read every one" P.S. works well), and expect the first
  email to a cold list to land mostly in Promotions.
- **Promotions is not spam.** It is still inbox delivery. Industry data puts read rates about 12%
  lower than Primary. Don't make the copy worse to chase the tab.

### Practical copy guidance

- Lead with something true and relevant to the reader (news, a teaching, thanks for something
  they did), not with the product.
- Mention the product once, plainly ("We call it X"), with no superlatives, and give it one
  button at the end.
- Don't hedge about your own product ("this may sound strange", "nothing to pay").
- Keep the unsubscribe header and footer. Compliance wins over tab placement.

## 3. How to run a placement test

Use `scripts/placement_test.py` (stdlib only). It sends a set of variant emails to one or more
seed inboxes, tags each subject `[PT<round>-<letter>]`, spaces sends 20 seconds apart, and appends
each send to a TSV log.

```bash
python scripts/placement_test.py --creds /path/to/mailer_creds.txt --to seed@example.com \
  --round 1 --unsub-mailto contact@example.org --unsub-url https://example.org/u/{token} \
  control.html variant_a.html variant_b.html
```

Each variant is an `.html` file whose `<title>` is the subject. A `.txt` file with the same stem,
if present, becomes the plain-text part; otherwise the script derives one from the HTML. Run
`--help` for every option, including `--dry-run`.

Then check the tab. With a Gmail connector or the Gmail API, search
`subject:PT<round> category:primary` and `subject:PT<round> category:promotions`. Gmail sorts on
arrival, so results are ready within a minute. (CATEGORY_* labels aren't returned in message
labelIds through the claude.ai connector, so search by category instead.)

Rules that keep the results meaningful:

- **Change one thing per variant**, and include a **known-Primary control** in every round so you
  can tell when the inbox itself has shifted.
- **Repeat a winner once** before trusting it.
- **Never open, move, star or reply to test emails** in a seed inbox. Gmail learns from that and
  contaminates later rounds. Delete them in bulk afterwards, without moving any to Primary first.
- **Use several seed inboxes,** including personal @gmail.com accounts with no history with the
  sender. One Workspace inbox is only a rough signal.
- **Log every result** (tag, variant, tab) in a TSV next to the campaign, and write conclusions
  into the campaign notes, so later campaigns build on them instead of re-running them.
