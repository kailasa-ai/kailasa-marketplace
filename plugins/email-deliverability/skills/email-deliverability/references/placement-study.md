# Gmail placement study (KAILASA, 2026-09-26 to 09-27)

**Context:** a reconnect campaign to ~65k past program participants who hadn't heard from us in
years. Every test of the first email landed in Gmail's Promotions tab, while a Navaratri Day 2
"thank you for joining the Marathon" email from the same sender landed in Primary. We ran 14
rounds of single-change variants (~75 emails) to one Google Workspace seed inbox, sent through
Kailasa Mailer with SPF, DKIM and DMARC all passing.

**Terms used below:**
- "Navaratri" means the Navaratri Day 2 email: a thank-you for a livestream, a long sadhana
  teaching, the launch of a Sadhana section in the app, and one "Enroll" button.
- "Our email" or "e01" means the reconnect email 1: a greeting, "you attended a program", a
  Swamiji quote, four paragraphs introducing Ask Nithyananda AI, a "what's on your mind" CTA,
  a button and a P.S.
- "Letter" means a fresh letter-style rewrite of e01.
- "Compliant" means the email carries the `List-Unsubscribe` header and a grey unsubscribe footer.

## Results by round

| Round | Question | Result |
|---|---|---|
| 1 | Is it the unsubscribe header, footer or layout? | Navaratri resent = Primary. Our email with or without List-Unsubscribe / footer / table button / blockquote = Promotions. **Not the technical stuff.** |
| 2 | Subject, link domain, headers? | Our body + Navaratri subject / kailasa.ai link / no links = Promotions. Navaratri body + our subject / ask.nithyananda.ai link / our Message-ID+Date = Primary. **It's the body text.** |
| 3 | Which paragraphs of ours? | Dropping any one group (intro, product, "receiving this email", claims, question+P.S., preheader) = still Promotions. |
| 4 | Mix paragraphs across the two emails | Navaratri + our 4 product paragraphs = **Promotions**. Navaratri + our intro / our CTA / our sign-off+P.S. / shortened to 137 words = Primary. Ours + Navaratri teaching = Promotions. |
| 5 | Each product paragraph alone in Navaratri; Navaratri + List-Unsubscribe | All Primary. **Signals add up; no single phrase flips it.** List-Unsubscribe alone doesn't flip strong content. |
| 6 | Light rewrites of our copy | All Promotions (even a skeleton of quote + question + button + P.S.). |
| 7 | Fresh letter-style draft (new text) | Letter = **Primary** (so it's style, not "Gmail has seen this text"). Letter + full layout (header+footer+table) / + "World's First AI… you'll love it" / our email as plain text = Promotions. |
| 8 | Letter + one layout element | + List-Unsubscribe = Promotions. + grey footer = Promotions. + table button = Primary. Repeat of letter = Primary (reproducible). |
| 9 | Can strong content survive the compliance signals? | **Navaratri + List-Unsubscribe + grey footer = Primary.** Expanded letter + header (± footer) = Promotions. |
| 10 | Letter (compliant) + community news / teaching / Navaratri teaching / Navaratri thank-you lines | All Promotions. |
| 11 | Compliant letter minus question+P.S. / preheader / sign-off; Navaratri compliant + our question+button | All Promotions — including **Navaratri + compliance + "So, what's been on your mind lately? Sounds like you already have a place to start." + button**. |
| 12 | Softer CTAs on the compliant letter; Navaratri compliant + our button only | Letter: sentence link / Navaratri-style CTA / other label / **no CTA at all** = Promotions. Navaratri + compliance + our "Ask Swamiji a question" button = **Primary**. |
| 13 | Pure touch-base email 1 (no product, no link), compliant | All Promotions (with or without a teaser P.S. or a one-line product mention). |
| 14 | Email 1 rewritten as community news (Navaratri Sadhana Marathon, quote, one product paragraph, button, "let us"), compliant | All Promotions: full, shorter opening, **no product and no button**, repeat. Control (the round 12 Primary variant, repeated) = Primary, so the inbox hadn't shifted. |

Also: five earlier manual tests (original email 01, with and without UTM tags, both subject lines) were all Promotions.

## Conclusions

1. **Tab placement is decided by the body text**, scored as a whole. Sender, SPF/DKIM/DMARC,
   subject, link domain, UTM tags, Message-ID/Date, button style: no effect in any test.
2. **Promotions weight:** product-introduction lines ("It's called…", "World's First AI made for
   Spirituality", "we think you'll love it", feature descriptions, "your first answer takes
   seconds"), the "what's been on your mind / place to start" line, and **the unsubscribe
   header and unsubscribe footer** (each adds weight).
3. **"It's been a long time since we were in touch" copy is borderline.** Without unsubscribe
   signals it lands Primary; with them it lands Promotions, even with no product, link or button.
4. **Primary weight:** the Navaratri pattern — a community update to people treated as part of
   the sangha (thanks for a shared event, "we / let us", a long sadhana reflection, one button at
   the end, no product claims). It stays Primary even with List-Unsubscribe + grey footer + our
   button.
5. **Round 14 closes the copy-tuning route.** A Navaratri-*style* community update written for
   this audience still lands Promotions with the compliance signals, even with no product. Only the
   actual Navaratri Day 2 text (long sadhana teaching, thanks for an event the reader attended)
   survives. For this seed inbox, any compliant email to long-unengaged readers lands Promotions.
   Stop tuning email 1 for the tab; choose copy on content and earn Primary through engagement
   (replies), then confirm on personal @gmail.com inboxes.

## Research sources (web, 2026-09-26)

- Google: support.google.com/a/answer/81126, support.google.com/a/answer/14229414,
  developers.google.com/gmail/promotab
- Mailgun: mailgun.com/blog/deliverability/gmails-promotions-tab-how-to-get-emails-classified-as-primary/
- Mailchimp: mailchimp.com/help/about-gmail-tabs/
- Tab read rates: zettasphere.com/gmail-promotions-tab-inbox-delivery-stats/
- Anecdote (removing list headers moved mail to Primary): forum.mailwizz.com/threads/some-headers-flagging-mails-to-google-promotions-bulk-mail-tab.593/
