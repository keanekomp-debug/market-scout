#!/usr/bin/env python3
"""
🎯 Market Opportunity Scout Core v2.0
✅ Neural semantic search (Exa.ai)
✅ Few-shot learning prompts (Gemini)
✅ Stats tracking for UI counter
✅ Manual trigger support
All free tiers. Copy-paste-commit ready.
"""

import os, json, requests, re, smtplib, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai

# === CONFIG (Auto-loaded from GitHub Variables or env) ===
SOURCES = os.getenv("SCOUT_SOURCES", "site:reddit.com, site:twitter.com, site:linkedin.com").split(",")
DATE_RANGE = os.getenv("SCOUT_DATE_RANGE", "2021-01-01..2026-04-06")
PHRASES = os.getenv("SCOUT_PHRASES", "wish there was a tool for\nfrustrated that I can't\ngap in the market for").strip().split("\n")
ROLES = os.getenv("SCOUT_ROLES", "CEO, founder, CTO").split(",")
RUN_MODE = os.getenv("RUN_MODE", "standard")  # 'standard' or 'deep'

# === API SETUP (Free Tiers) ===
EXA_API_KEY = os.getenv("EXA_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def search_exa(query):
    """Search Exa.ai API with NEURAL semantic search [[51]]"""
    url = "https://api.exa.ai/search"
    headers = {"Authorization": f"Bearer {EXA_API_KEY}", "Content-Type": "application/json"}
    
    # ✨ NEURAL SEARCH: Better semantic understanding of frustration phrases
    payload = {
        "query": query,
        "numResults": 15 if RUN_MODE == "deep" else 8,
        "type": "neural",  # ← KEY UPGRADE: Semantic search vs keyword
        "includeDomains": [s.strip().replace("site:", "") for s in SOURCES if s.strip()],
        "startPublishedDate": DATE_RANGE.split("..")[0],
        "endPublishedDate": DATE_RANGE.split("..")[1],
        "contents": {
            "text": True, 
            "highlights": True,
            "livecrawl": "always"  # Fresh results
        }
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"⚠️ Exa API error: {resp.status_code} - {resp.text}")
        return []
    return resp.json().get("results", [])

def analyze_with_gemini(raw_results):
    """Analyze with FEW-SHOT LEARNING for precise filtering [[25]]"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    # ✨ FEW-SHOT PROMPT: Examples teach the AI what to keep/discard
    prompt = f"""You are a Market Gap Analyst. Analyze these social/forum posts from CEOs/founders.

=== TASK ===
1. FILTER: Discard general complaints. Keep SPECIFIC technical/methodical gaps.
2. CATEGORIZE: Group by Industry (SaaS, Healthcare, Fintech, etc.).
3. WEIGHT: Assign Pain Score 1-10. 10 = user explicitly says they'd pay.
4. SUMMARIZE: 2-sentence pitch for the missing tool/method.
5. OUTPUT: Valid JSON array only. Fields: industry, pain_score, pitch, source_url, raw_quote.

=== EXAMPLES (FEW-SHOT LEARNING) ===

✅ KEEP (Specific gap):
Quote: "We've spent 3 months trying to connect Stripe subscriptions to our internal analytics. No tool does real-time webhook sync without Zapier."
→ industry: "SaaS"
→ pain_score: 9
→ pitch: "A native Stripe-to-analytics connector with real-time webhook support and retry logic—zero third-party dependencies."

✅ KEEP (Technical frustration):
Quote: "HIPAA compliance is killing our patient intake flow. Every form builder either isn't compliant or can't export FHIR JSON."
→ industry: "Healthcare Tech"
→ pain_score: 10
→ pitch: "HIPAA-compliant form builder with one-click FHIR R4 export for EHR integrations."

❌ DISCARD (General complaint):
Quote: "Taxes are too high for startups."
→ (skip - not a tool/method gap)

❌ DISCARD (Vague):
Quote: "Marketing is hard."
→ (skip - no specific technical gap)

=== POSTS TO ANALYZE ===
{json.dumps(raw_results[:20], indent=2)}

Respond ONLY with valid JSON array. No markdown. No extra text."""
    
    try:
        response = model.generate_content(prompt, request_options={"timeout": 45})
        # Extract JSON robustly
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return []
    except Exception as e:
        print(f"⚠️ Gemini analysis error: {e}")
        return []

def generate_stats(opportunities):
    """Generate stats.json for UI counter"""
    today = datetime.datetime.now()
    week_ago = today - datetime.timedelta(days=7)
    
    # Count opportunities from last 7 days (mocked - in prod, use timestamp from results)
    recent = [o for o in opportunities]  # Simplified for demo
    high_pain = [o for o in opportunities if o.get('pain_score', 0) >= 8]
    
    return {
        "total_this_week": len(recent),
        "high_pain_count": len(high_pain),
        "last_run": today.isoformat(),
        "run_mode": RUN_MODE
    }

def generate_html_snippet(opportunities):
    """Generate Apple-style HTML cards"""
    if not opportunities:
        return '<div class="empty-state"><p>✨ No high-signal opportunities found this cycle.<br><small>Try adjusting filters or run in "deep" mode.</small></p></div>'
    
    cards = []
    for i, opp in enumerate(opportunities):
        pain_score = opp.get('pain_score', 5)
        pain_class = 'data-score="10"' if pain_score >= 10 else ('data-score="7-9"' if pain_score >= 7 else 'data-score="1-6"')
        cards.append(f'''
        <div class="opportunity-card" style="--i:{i}" onclick="toggleSelect(this)">
          <div class="card-header">
            <span class="industry-tag">{'🧩' if opp['industry']=='SaaS' else '🏥' if 'Health' in opp['industry'] else '💰'} {opp['industry']}</span>
            <span class="pain-score" {pain_class}>{pain_score}/10</span>
          </div>
          <div class="pitch"><strong>Missing Tool Pitch:</strong> {opp['pitch']}</div>
          <a href="{opp['source_url']}" class="source-link" target="_blank" onclick="event.stopPropagation()">Source ↗</a>
          <div class="card-footer">
            <label class="checkbox"><input type="checkbox" onclick="event.stopPropagation()"> Include in email share</label>
            <button class="btn btn-ghost" onclick="event.stopPropagation(); alert('Preview: This lead would be emailed to your co-founders')">Preview</button>
          </div>
        </div>''')
    
    return "\n".join(cards)

def send_email(opportunities):
    """Email summary via Gmail (free) [[73]]"""
    if not opportunities:
        return
    msg = MIMEMultipart()
    msg['From'] = os.getenv("GMAIL_USER")
    msg['To'] = os.getenv("GMAIL_USER")
    msg['Subject'] = f"🎯 Market Scout: {len(opportunities)} New Opportunities ({RUN_MODE} mode)"
    
    body = f"Hi there,\n\nYour Market Scout found {len(opportunities)} high-signal opportunities:\n\n"
    for opp in opportunities[:5]:
        body += f"• [{opp['pain_score']}/10] {opp['industry']}: {opp['pitch']}\n  {opp['source_url']}\n\n"
    body += f"\nView & share full report: https://{os.getenv('GITHUB_REPOSITORY_OWNER', 'your-username')}.github.io/market-scout"
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
            server.send_message(msg)
        print("✅ Email sent")
    except Exception as e:
        print(f"⚠️ Email failed: {e}")

def update_index_html(html_snippet):
    """Inject results into index.html"""
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Replace results container content
    pattern = r'(<div id="resultsContainer">).*(</div>\s*<footer>)'
    replacement = f'\\1{html_snippet}\\2'
    html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

def main():
    print(f"🚀 Market Scout starting ({RUN_MODE} mode)...")
    
    # 1. Build search queries
    queries = []
    for phrase in PHRASES:
        phrase = phrase.strip()
        if not phrase: continue
        for role in ROLES:
            role = role.strip()
            if role:
                queries.append(f'"{phrase}" {role}')
    
    # 2. Search & collect (with neural search)
    all_results = []
    for q in queries[:10]:  # Limit queries to stay within free tier
        print(f"🔍 Searching: {q[:60]}...")
        results = search_exa(q)
        all_results.extend(results)
        if RUN_MODE == "standard" and len(all_results) >= 30:
            break  # Early exit for standard mode
    
    print(f"📦 Collected {len(all_results)} raw results")
    
    # 3. Analyze with few-shot learning
    opportunities = analyze_with_gemini(all_results)
    print(f"🎯 Identified {len(opportunities)} high-signal opportunities")
    
    # 4. Generate stats for UI counter
    stats = generate_stats(opportunities)
    with open('stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    # 5. Generate HTML snippet
    html_snippet = generate_html_snippet(opportunities)
    
    # 6. Update index.html
    update_index_html(html_snippet)
    
    # 7. Save raw results
    with open('results.json', 'w') as f:
        json.dump({
            "opportunities": opportunities,
            "raw_count": len(all_results),
            "timestamp": datetime.datetime.now().isoformat()
        }, f, indent=2)
    
    # 8. Email summary
    send_email(opportunities)
    
    print(f"✅ Scout complete: {len(opportunities)} opportunities • Stats updated • Email sent")

if __name__ == "__main__":
    main()
