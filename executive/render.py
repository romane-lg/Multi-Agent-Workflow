"""Deterministic, escaped Markdown and standalone HTML from one brief."""
from html import escape
from urllib.parse import urlsplit

from executive.schema import ExecutiveBrief, TITLES
from executive.validation import prose_fields, word_count


STATUS_LABELS = {"recommend": "Proposed decision", "propose_test": "Test first", "needs_evidence": "Evidence needed"}


def safe_url(url):
    return url if urlsplit(url).scheme in ("https", "http") else "#"


def presentation_data(brief: ExecutiveBrief, payload: dict):
    analysis = payload["analysis"]
    report = analysis["analyst_report"]
    upstream = analysis["upstream_handoff"]
    researcher = upstream["researcher_output"]
    insights = {i["insight_id"]: i for i in report["market_insights"]}
    findings = {f["finding_id"]: f for f in researcher["evidence_pack"]["findings"]}
    sources = {a["article_id"]: a for a in researcher["sources"]}
    recs = {r["focus"]: r for r in report["recommendations"]}

    def citations(ids):
        refs = set()
        for insight_id in ids:
            evidence = insights[insight_id]["evidence"]
            refs.update((c["article_id"], c["paragraph_id"]) for c in evidence["citations"])
            for finding_id in evidence["finding_ids"]:
                refs.update((c["article_id"], c["paragraph_id"]) for c in findings[finding_id]["citations"])
        return sorted(refs)

    all_refs = citations(list(insights))
    article_ids = sorted({a for a, _ in all_refs}, key=lambda a: (sources[a]["publication_date"], a))
    numbers = {aid: n for n, aid in enumerate(article_ids, 1)}
    ledger = [{"number": numbers[aid], "title": sources[aid]["title"], "date": sources[aid]["publication_date"],
               "url": safe_url(sources[aid].get("normalized_url", sources[aid]["url"])),
               "paragraphs": sorted({pid for a, pid in all_refs if a == aid})} for aid in article_ids]
    ref_numbers = lambda ids: sorted({numbers[aid] for aid, _ in citations(ids)})
    cards = []
    for focus, title in TITLES.items():
        rec = recs[focus]
        cards.append({"focus": focus, "title": title, **getattr(brief.topics, focus).model_dump(),
                      "status": STATUS_LABELS[rec["decision_status"]],
                      "recommendation_id": rec["recommendation_id"],
                      "source_numbers": ref_numbers(rec["insight_ids"]), "brief_pages": rec["brief_pages"]})
    competitors = report["competitor_comparison"]
    covered = ", ".join(c["company"] for c in competitors if c["evidence_status"] == "covered") or "None"
    missing = ", ".join(c["company"] for c in competitors if c["evidence_status"] == "no_evidence") or "None"
    dates = sorted(a["publication_date"] for a in researcher["sources"] if a["availability"] == "full_text")
    return {"report": report, "cards": cards, "ledger": ledger,
            "signals": [{"text": s.text, "numbers": ref_numbers(s.insight_ids)} for s in brief.market_signals],
            "covered": covered, "missing": missing,
            "sample_dates": f"{dates[0]}–{dates[-1]}" if dates else "No article dates",
            "prose_word_count": sum(word_count(text) for text, _ in prose_fields(brief))}


def render_markdown(brief: ExecutiveBrief, payload: dict):
    data = presentation_data(brief, payload)
    held = payload["publication_status"] != "review_passed"
    refs = lambda ns: " ".join(f"[{n}](#source-{n})" for n in ns)
    clean = lambda text: escape(text.replace("\n", " "))
    lines = ["# Fizzera | Strategic outlook", f"As of {data['report']['as_of_date']} · Historical article sample: {data['sample_dates']}",
             "**Working brief — pending human review. Actions are proposals; unresolved review findings remain.**" if held else
             "**Model review completed. Actions remain management proposals; source limits still apply.**",
             "## Strategic outlook", clean(brief.strategic_outlook),
             "**First priorities:** " + " → ".join(TITLES[f] for f in brief.priority_focuses),
             "## Market signals"]
    lines.append("\n".join(f"- {clean(s['text'])} {refs(s['numbers'])}" for s in data["signals"]))
    lines.append("## Decisions by topic")
    for card in data["cards"]:
        lines.extend([f"### {card['title']} · {card['status']}",
                      f"**Implication:** {clean(card['implication'])}",
                      f"**Next action:** {clean(card['action'])}",
                      f"**Proposed measure / gate:** {clean(card['metric_or_gate'])}",
                      f"**Watch-out:** {clean(card['caveat'])}",
                      f"{refs(card['source_numbers'])} · Company brief pp. {', '.join(map(str, card['brief_pages']))}"])
    lines.extend(["## Coverage & confidence", f"**Covered:** {data['covered']}. **Evidence gaps:** {data['missing']}.",
                  "Historical, limited sample; reported outcomes do not establish causal ROI or Canadian applicability. Company figures are planning context, including fictional survey data and forecasts.",
                  "## Sources"])
    for source in data["ledger"]:
        lines.extend([f"<a id=\"source-{source['number']}\"></a>",
                      f"{source['number']}. [{clean(source['title'])}]({source['url']}) · {source['date']} · paragraphs {', '.join(source['paragraphs'])}"])
    return "\n\n".join(lines) + "\n"


def render_html(brief: ExecutiveBrief, payload: dict):
    data = presentation_data(brief, payload)
    held = payload["publication_status"] != "review_passed"
    e = escape
    refs = lambda ns: " ".join(f'<a class="ref" href="#source-{n}" aria-label="Source {n}">[{n}]</a>' for n in ns)
    priorities = "".join(f'<span><b>{n:02}</b> {e(TITLES[f])}</span>' for n, f in enumerate(brief.priority_focuses, 1))
    signals = "".join(f'<li>{e(s["text"])} {refs(s["numbers"])}</li>' for s in data["signals"])
    cards = []
    for n, card in enumerate(data["cards"], 1):
        cards.append(f'''<article class="card"><div class="card-top"><span class="eyebrow">{n:02} / DECISION AREA</span><span class="tag">{e(card['status'])}</span></div>
<h3>{e(card['title'])}</h3><p class="implication">{e(card['implication'])}</p>
<dl><dt>Next action</dt><dd>{e(card['action'])}</dd><dt>Proposed measure / gate</dt><dd>{e(card['metric_or_gate'])}</dd></dl>
<p class="caveat"><b>Watch-out</b> {e(card['caveat'])}</p><div class="card-source">{refs(card['source_numbers'])} <span>Company brief pp. {e(', '.join(map(str, card['brief_pages'])))}</span></div></article>''')
    ledger = "".join(f'<li id="source-{s["number"]}"><a href="{e(s["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{e(s["title"])}</a><small>{e(s["date"])} · paragraphs {e(", ".join(s["paragraphs"]))}</small></li>' for s in data["ledger"])
    banner = ("Working brief · pending human review", "Actions are proposals. Unresolved review findings remain.") if held else (
        "Model review completed", "Actions remain management proposals. Source limits still apply.")
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fizzera | Strategic outlook</title><style>
:root{--ink:#132c35;--muted:#536971;--teal:#006959;--paper:#f4f5f0;--line:#d9e3df;--white:#fff}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1080px;margin:auto;padding:44px 40px}header{border-top:5px solid var(--teal);padding-top:22px}.eyebrow{font-size:11px;font-weight:750;letter-spacing:.14em;color:var(--teal)}h1{font-size:clamp(32px,5vw,48px);line-height:1.1;letter-spacing:-.04em;margin:12px 0}h2{font-size:21px;letter-spacing:-.025em;margin:30px 0 14px}h3{font-size:23px;line-height:1.2;letter-spacing:-.025em;margin:16px 0 12px}p{margin:8px 0}.meta{font-size:12px;color:var(--muted)}.banner{display:flex;gap:14px;flex-wrap:wrap;background:#fff3db;border:1px solid #e6c983;border-radius:8px;padding:10px 14px;font-size:12px;margin:22px 0}.banner b{color:#785319}.outlook{background:var(--ink);color:white;border-radius:12px;padding:24px 28px;margin-top:24px}.outlook h2{margin:0 0 10px;color:#8ee0c9}.outlook p{font-size:19px;line-height:1.55;margin:0}.priorities{display:flex;gap:12px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding:20px 0}.priorities span{font-size:13px;margin-right:16px}.priorities b{color:var(--teal);margin-right:7px}.signals{background:#e8eeea;padding:18px 24px;border-radius:10px}.signals ul{margin:0;padding-left:18px}.signals li{padding:5px 0;font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.card{background:var(--white);border:1px solid var(--line);border-radius:12px;padding:23px;break-inside:avoid}.card:last-child{grid-column:1/-1}.card-top{display:flex;justify-content:space-between;align-items:center;gap:12px}.tag{border-radius:30px;padding:4px 9px;background:#e7f1ec;color:#175c4a;font-size:10px;font-weight:700;white-space:nowrap}.implication{font-size:14px;color:var(--muted)}dl{margin:16px 0}dt{font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--teal);margin-top:13px}dd{margin:4px 0 0;font-size:14px}.caveat{padding-top:12px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}.caveat b{color:var(--ink);margin-right:5px}.card-source{margin-top:13px;font-size:10px;color:var(--muted)}.card-source span{margin-left:6px}a{color:var(--teal);text-underline-offset:3px}.ref{font-size:11px;white-space:nowrap}.coverage{font-size:13px;padding:18px 0;border-bottom:1px solid var(--line)}.coverage p{margin:5px 0}.fine{font-size:11px;color:var(--muted)}details{margin-top:24px}summary{cursor:pointer;font-size:13px;font-weight:700}details ol{padding-left:22px;font-size:12px}details li{margin:12px 0}small{display:block;color:var(--muted);font-size:10px}footer{font-size:10px;color:var(--muted);margin-top:24px}
@media(max-width:680px){main{padding:24px 18px}.grid{grid-template-columns:1fr}.card:last-child{grid-column:auto}.outlook{padding:20px}.outlook p{font-size:17px}.card-top{align-items:flex-start}.priorities{gap:8px}.banner{gap:4px}}
@media print{@page{size:A4;margin:13mm}body{background:white;font-size:10pt}main{padding:0;max-width:none}h1{font-size:27pt}h2{font-size:14pt;margin-top:18px}h3{font-size:15pt}.outlook{background:white!important;color:var(--ink);border:1px solid var(--line);padding:16px}.outlook h2{color:var(--teal)}.outlook p{font-size:11pt}.grid{gap:10px}.card{padding:14px}.card dd,.implication{font-size:9pt}.banner{margin:12px 0}.signals li{font-size:9pt}a{color:inherit}.priorities{padding:12px 0}details{display:block}.card{break-inside:avoid}footer{margin-top:14px}}
</style></head><body><main>''' + f'''
<header><div class="eyebrow">FIZZERA / COMPETITIVE INTELLIGENCE</div><h1>Strategic outlook</h1><p class="meta">As of {e(data['report']['as_of_date'])} · Historical source sample {e(data['sample_dates'])} · Executive brief</p></header>
<div class="banner" role="note"><b>{e(banner[0])}</b><span>{e(banner[1])}</span></div>
<section class="outlook"><h2>The strategic call</h2><p>{e(brief.strategic_outlook)}</p></section>
<nav class="priorities" aria-label="Priority order">{priorities}</nav>
<section><h2>What the market signals</h2><div class="signals"><ul>{signals}</ul></div></section>
<section><h2>What Fizzera should do next</h2><div class="grid">{''.join(cards)}</div></section>
<section class="coverage"><p><b>Covered:</b> {e(data['covered'])}.</p><p><b>Evidence gaps:</b> {e(data['missing'])}.</p><p class="fine">Historical, limited sample; reported outcomes do not establish causal ROI or Canadian applicability. Company figures are planning context, including fictional survey data and forecasts.</p></section>
<details><summary>Sources &amp; traceability · {len(data['ledger'])} cited articles</summary><ol>{ledger}</ol></details>
<footer>Fizzera management working material · Source links and company-brief page references preserve traceability.</footer>
</main></body></html>'''
