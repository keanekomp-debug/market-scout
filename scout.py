#!/usr/bin/env python3
"""
🎯 Market Opportunity Scout Core
- Searches Exa.ai for founder frustrations
- Analyzes with Gemini API
- Outputs Apple-style HTML report
- Emails you the summary
All free tiers. No code changes needed.
"""

import os, json, requests, re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai

# === CONFIG (Auto-loaded from index.html localStorage in production) ===
SOURCES = os.getenv("SCOUT_SOURCES", "site:reddit.com, site:twitter.com, site:linkedin.com").split(",")
DATE_RANGE = os.getenv("SCOUT_DATE_RANGE", "2021-01-01..2026-04-06")
PHRASES = os.getenv("SCOUT_PHRASES", "wish there was a tool for\nfrustrated that I can't\ngap in the market for").strip().split("\n")
ROLES = os.getenv("SCOUT_ROLES", "CEO, founder, CTO").split(",")

# === API SETUP (Free Tiers) ===
EXA_API_KEY = os.getenv("EXA_API_KEY")
GEMINI_API_KEY = os.getenv("EMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def search_exa(query):
    """Search Exa.ai API (free tier: 1k requests/month) [[51]]"""
    url = "https://api.exa.ai/search"
    headers = {"Authorization": f"Bearer {EXA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "query": query,
        "numResults": 10,
        "includeDomains": [s.strip().replace("site:", "") for s in SOURCES if s.strip()],
        "startPublishedDate": DATE_RANGE.split("..")[0],
        "endPublishedDate": DATE_RANGE.split("..")[1],
        "contents": {"text": True, "highlights": True}
    }
    resp = requests.post(url, json=payload, headers=headers)
    return resp.json().get("results", [])

def analyze_with_gemini(raw_results):
    """Filter, score, and summarize using Gemini (free tier) [[25]]"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    # Build prompt from your exact instructions
    prompt = f"""You are a Market Gap Analyst. Analyze these social/forum posts from CEOs/founders.

TASK:
1. FILTER: Discard general complaints ('taxes are high'). Keep SPECIFIC technical/methodical gaps ('can't integrate X with Y').
2. CATEGORIZE: Group by Industry (SaaS, Healthcare, Fintech, etc.).
3. WEIGHT: Assign Pain Score 1-10. 10 = user explicitly says they'd pay for solution.
4. SUMMARIZE: 2-sentence pitch for the missing tool/method.
5. OUTPUT: Clean JSON array with fields: industry, pain_score, pitch, source_url, raw_quote.

POSTS TO ANALYZE:
{json.dumps(raw_results[:15], indent=2)}  # Limit to avoid token limits

Respond ONLY with valid JSON array. No markdown, no extra text."""
    
    response = model.generate_content(prompt)
    try:
        # Extract JSON from response
        json_str = re.search(r'\[.*\]', response.text, re.DOTALL).group()
        return json.loads(json_str)
    except:
        # Fallback: return empty if parsing fails
        return []

def generate_html(opportunities):
    """Generate Apple-style HTML report (injects into index.html)"""
    if not opportunities:
        return '<div class="empty-state"><p>✨ No high-signal opportunities found this cycle. Adjust filters and try again.</p></div>'
    
    cards = []
    for opp in opportunities:
        pain_class = 'data-score="10"' if opp['pain_score'] >= 10 else ('data-score="7-9"' if opp['pain_score'] >= 7 else 'data-score="1-6"')
        cards.append(f'''
        <div class="opportunity-card" onclick="toggleSelect(this)">
          <div class="card-header">
            <span class="industry-tag">{opp['industry']}</span>
            <span class="pain-score" {pain_class}>{opp['pain_score']}/10</span>
          </div>
          <div class="pitch"><strong>Missing Tool Pitch:</strong> {opp['pitch']}</div>
          <a href="{opp['source_url']}" class="source-link" target="_blank">Source ↗</a>
          <div style="margin-top:12px"><label class="checkbox"><input type="checkbox"> Include in email share</label></div>
        </div>''')
    
    return "\n".join(cards)

def send_email(opportunities):
    """Email summary via Gmail (free) [[73]]"""
    if not opportunities:
        return
    msg = MIMEMultipart()
    msg['From'] = os.getenv("GMAIL_USER")
    msg['To'] = os.getenv("GMAIL_USER")  # Send to yourself
    msg['Subject'] = f"🎯 Market Scout: {len(opportunities)} New Opportunities"
    
    body = "Hi there,\n\nYour Market Scout found these high-pain opportunities:\n\n"
    for opp in opportunities[:5]:  # Top 5 only
        body += f"• [{opp['pain_score']}/10] {opp['industry']}: {opp['pitch']}\n  {opp['source_url']}\n\n"
    body += "\nView full report: https://YOUR-USERNAME.github.io/market-scout"
    
    msg.attach(MIMEText(body, 'plain'))
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
        server.send_message(msg)

def main():
    # 1. Build search queries
    queries = []
    for phrase in PHRASES:
        for role in ROLES:
            queries.append(f'"{phrase.strip()}" {role.strip()}')
    
    # 2. Search & collect
    all_results = []
    for q in queries:
        results = search_exa(q)
        all_results.extend(results)
    
    # 3. Analyze
    opportunities = analyze_with_gemini(all_results)
    
    # 4. Generate HTML snippet
    html_snippet = generate_html(opportunities)
    
    # 5. Update index.html (inject results into #resultsContainer)
    with open('index.html', 'r') as f:
        html = f.read()
    # Simple injection: replace placeholder div
    html = re.sub(
        r'(<div id="resultsContainer">).*(</div>\s*<footer>)',
        f'\\1{html_snippet}\\2',
        html,
        flags=re.DOTALL
    )
    with open('index.html', 'w') as f:
        f.write(html)
    
    # 6. Save raw results for debugging
    with open('results.json', 'w') as f:
        json.dump(opportunities, f, indent=2)
    
    # 7. Email you
    send_email(opportunities)
    print(f"✅ Scout complete: {len(opportunities)} opportunities found")

if __name__ == "__main__":
    main()
