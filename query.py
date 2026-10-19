# Sorry if this code looks unconventional eg; the inline templates etc, it is because it was made on an Android, no PC.
import os
os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_ALLOWED_HOSTS"] = "*" 
from nanodjango import Django
from django.http import HttpResponse, JsonResponse
from django.template import Template, Context
from django.db import models
from urllib.parse import urlencode          # safely builds ?q=hello+world
from urllib.request import urlopen, Request # makes the HTTP GET request
import json as _json               
app = Django(

)

# Helper: render an inline template string with a context dict.
# Template(source).render(Context(ctx)) is exactly what Django's
# render() shortcut does behind the scenes - we just skip the file lookup.
def render_html(source, ctx):
    return HttpResponse(Template(source).render(Context(ctx)))

# INLINE TEMPLATE #1: the main page (home view + search/history view).
# Everything the user SEES: both screens, the dark theme CSS, and the
# JavaScript that swaps views and talks to our Django routes.
INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mini Search Engine</title>
<style>
  /* CSS variables = the dark theme from your screenshots */
  :root {
    --bg: #1f1f1f; --surface: #303134; --surface-2: #3c4043;
    --text: #e8eaed; --text-dim: #9aa0a6; --accent: #8ab4f8;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; font-family: Arial, sans-serif; }
  body { background: var(--bg); color: var(--text); min-height: 100vh; }

  /* ---- HOME SCREEN: logo centered, big fake search bar ---- */
  #homeScreen {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 100vh; padding: 20px;
  }
  /* gradient text = the colorful Google logo effect */
  .logo {
    font-size: 64px; font-weight: bold; letter-spacing: -2px; margin-bottom: 28px;
    background: linear-gradient(90deg, #4285f4, #ea4335, #fbbc05, #34a853, #4285f4);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .search-bar {
    display: flex; align-items: center; gap: 12px;
    width: 100%; max-width: 560px; height: 48px;
    background: var(--surface); border-radius: 24px; padding: 0 20px;
    cursor: text; transition: box-shadow .2s;
  }
  .search-bar:hover { box-shadow: 0 1px 6px rgba(0,0,0,.5); }
  .search-bar svg { flex-shrink: 0; fill: var(--text-dim); }
  .search-bar span { color: var(--text-dim); font-size: 16px; flex: 1; }

  /* ---- SEARCH SCREEN: hidden by default, shown when bar is clicked ---- */
  #searchScreen {
    display: none; flex-direction: column; min-height: 100vh;
    animation: fadeIn .18s ease;   /* the smooth app-like transition */
  }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  .search-header {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-bottom: 1px solid #3c4043;
    position: sticky; top: 0; background: var(--bg); z-index: 10;
  }
  .icon-btn { background: none; border: none; cursor: pointer; padding: 8px;
    border-radius: 50%; display: flex; align-items: center; }
  .icon-btn:hover { background: var(--surface-2); }
  .icon-btn svg { fill: var(--text); width: 22px; height: 22px; }
  #searchInput { flex: 1; background: none; border: none; outline: none;
    color: var(--text); font-size: 18px; caret-color: var(--accent); }

  /* ---- HISTORY ROWS: clock icon + query + hidden delete button ---- */
  #historyList { padding: 8px 0; }
  .history-item { display: flex; align-items: center; gap: 18px;
    padding: 12px 20px; cursor: pointer; }
  .history-item:hover { background: var(--surface-2); }
  .history-item .clock { width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
    background: var(--surface-2); display: flex; align-items: center; justify-content: center; }
  .history-item .clock svg { width: 16px; height: 16px; fill: var(--text-dim); }
  .history-item .label { flex: 1; font-size: 17px; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; }
  /* the X only appears when you hover the row, just like the real app */
  .history-item .remove { background: none; border: none; color: var(--text-dim);
    cursor: pointer; font-size: 18px; padding: 4px 8px; border-radius: 50%; visibility: hidden; }
  .history-item:hover .remove { visibility: visible; }
  .history-item .remove:hover { color: var(--text); }
  #clearAll { margin: 8px 20px; padding: 8px 14px; align-self: flex-start;
    background: var(--surface); color: var(--text-dim); border: none;
    border-radius: 16px; cursor: pointer; font-size: 13px; }
  #clearAll:hover { color: var(--text); }
  .hint { color: var(--text-dim); text-align: center; padding: 30px; font-size: 14px; }

  /* ---- AUTOCOMPLETE DROPDOWN: slides under the header ---- */
  #suggestions { display: none; position: sticky; top: 57px; z-index: 9;
    background: var(--bg); border-bottom: 1px solid #3c4043; padding: 4px 0; }
  .suggestion-item { display: flex; align-items: center; gap: 18px;
    padding: 12px 20px; cursor: pointer; font-size: 17px; }
  .suggestion-item:hover, .suggestion-item.active { background: var(--surface-2); }
  .suggestion-item svg { width: 18px; height: 18px; fill: var(--text-dim); flex-shrink: 0; }
  .suggestion-item mark { background: none; color: var(--accent); font-weight: bold; }

  /* ---- RESULT CARDS ---- */
  #results { padding: 16px 20px; max-width: 700px; width: 100%; margin: 0 auto; }
  .result-card { background: var(--surface); border-radius: 12px;
    padding: 14px 16px; margin-bottom: 12px; }
  .result-card h3 { font-size: 16px; color: var(--accent); margin-bottom: 6px; }
  .result-card p { color: var(--text-dim); font-size: 14px; line-height: 1.5; }
  .result-card a { color: var(--accent); font-size: 13px; word-break: break-all; }
</style>
</head>
<body>

<!-- HOME SCREEN: clicking the bar triggers JS that swaps the views -->
<div id="homeScreen">
  <div class="logo">Search</div>
  <div class="search-bar" id="openSearch">
    <svg width="20" height="20" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
    <span>Search</span>
    <svg width="20" height="20" viewBox="0 0 24 24"><path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11z"/></svg>
  </div>
</div>

<!-- SEARCH SCREEN: header with back arrow + input, then history, results -->
<div id="searchScreen">
  <div class="search-header">
    <button class="icon-btn" id="goBack" title="Back">
      <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
    </button>
    <input id="searchInput" type="text" placeholder="Search..." autocomplete="off">
  </div>
  <div id="suggestions"></div>   <!-- autocomplete dropdown (hidden until typing) -->
  <div id="historyList"></div>   <!-- filled by Django via /history/ -->
  <button id="clearAll">Clear search history</button>
  <div id="results"></div>       <!-- filled by Django via /search/ -->
</div>

<script>
// ---- Grab all the elements we need once, at page load ----
const homeScreen  = document.getElementById('homeScreen');
const searchScreen = document.getElementById('searchScreen');
const searchInput = document.getElementById('searchInput');
const historyList = document.getElementById('historyList');
const clearAllBtn = document.getElementById('clearAll');
const resultsDiv  = document.getElementById('results');
const suggBox     = document.getElementById('suggestions');

// ---- VIEW SWITCHING: this is the whole "click bar -> history screen" trick ----
// It's just two divs; JS shows one and hides the other, then focuses the input.
document.getElementById('openSearch').addEventListener('click', () => {
  homeScreen.style.display = 'none';
  searchScreen.style.display = 'flex';
  clearAllBtn.style.display = '';
  loadHistory();          // ask Django for this user's session history
  searchInput.focus();
});
document.getElementById('goBack').addEventListener('click', () => {
  searchScreen.style.display = 'none';
  homeScreen.style.display = 'flex';
  searchInput.value = '';
  resultsDiv.innerHTML = '';
  hideSuggestions();
});

// ---- HISTORY: Django stores it in the session, we just fetch rendered HTML ----
async function loadHistory() {
  const res = await fetch('/history/');
  historyList.innerHTML = await res.text();   // fragment contains the rows
}

// Click a history row to search it again; click the X to delete just that row
historyList.addEventListener('click', async e => {
  if (e.target.classList.contains('remove')) {
    const res = await fetch('/history/remove/' + e.target.dataset.index + '/');
    historyList.innerHTML = await res.text();
    return;
  }
  const item = e.target.closest('.history-item');
  if (item) {
    searchInput.value = item.querySelector('.label').textContent;
    doSearch();
  }
});
clearAllBtn.addEventListener('click', async () => {
  const res = await fetch('/history/clear/');
  historyList.innerHTML = await res.text();
});

// ---- SEARCH: Enter key triggers the search against our Django route ----
searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

async function doSearch() {
  const q = searchInput.value.trim();
  if (!q) return;
  hideSuggestions();
  historyList.innerHTML = '';
  clearAllBtn.style.display = 'none';
  resultsDiv.innerHTML = '<div class="hint">Searching...</div>';

  // Django calls DuckDuckGo server-side and returns ready-made HTML cards.
  // The JS never touches DuckDuckGo directly - simpler and no CORS issues.
  try {
    const res = await fetch('/search/?q=' + encodeURIComponent(q));
    resultsDiv.innerHTML = await res.text();
  } catch {
    resultsDiv.innerHTML = '<div class="hint">Network error - try again.</div>';
  }
}

// ---- AUTOCOMPLETE: debounced so we don't fire a request per keystroke ----
let debounceTimer;
searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);                 // cancel the previous timer
  const q = searchInput.value.trim();
  if (q.length < 2) { hideSuggestions(); return; }  // don't search for 1 letter
  debounceTimer = setTimeout(async () => {     // wait 200ms of idle typing
    try {
      const res = await fetch('/autocomplete/?q=' + encodeURIComponent(q));
      const items = await res.json();
      renderSuggestions(items, q);
    } catch { hideSuggestions(); }
  }, 200);
});

// Build the dropdown: magnifier icon + suggestion with the typed text highlighted
function renderSuggestions(items, q) {
  if (!items.length) { hideSuggestions(); return; }
  const qEsc = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');   // regex-escape the query
  suggBox.innerHTML = items.map(s => `
    <div class="suggestion-item" data-q="${s.replace(/"/g, '&quot;')}">
      <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
      <span>${s.replace(new RegExp('(' + qEsc + ')', 'ig'), '<mark>$1</mark>')}</span>
    </div>`).join('');
  suggBox.style.display = 'block';    // show dropdown...
  historyList.style.display = 'none'; // ...and hide history while typing
}
function hideSuggestions() {
  suggBox.style.display = 'none';
  suggBox.innerHTML = '';
  historyList.style.display = '';
}
// Clicking a suggestion fills the box and runs the search immediately
suggBox.addEventListener('click', e => {
  const item = e.target.closest('.suggestion-item');
  if (item) {
    searchInput.value = item.dataset.q;
    doSearch();
  }
});
</script>
</body>
</html>
"""
RESULTS_HTML = r"""
{% if error %}
<div class="hint">Error: {{ error }}</div>
{% elif results %}
  {% for r in results %}
  <div class="result-card">
    <h3>{{ r.title }}</h3>
    <p>{{ r.body }}</p>
    {% if r.url %}<a href="{{ r.url }}" target="_blank" rel="noopener">{{ r.url }}</a>{% endif %}
  </div>
  {% endfor %}
{% else %}
<div class="hint">No instant answer found for "{{ q }}".</div>
{% endif %}
"""
# INLINE TEMPLATE #3: history rows (also a fragment, pasted into #historyList)
# forloop.counter0 = Django's 0-based index, used by the remove endpoint.
HISTORY_HTML = r"""
{% if history %}
  {% for q in history %}
  <div class="history-item" data-index="{{ forloop.counter0 }}">
    <span class="clock">
      <svg viewBox="0 0 24 24"><path d="M11.99 2a10 10 0 1 0 10 10A10 10 0 0 0 11.99 2zM12 20a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
    </span>
    <span class="label">{{ q }}</span>
    <button class="remove" data-index="{{ forloop.counter0 }}" title="Remove">&#10005;</button>
  </div>
  {% endfor %}
{% else %}
<div class="hint">No recent searches</div>
{% endif %}
"""
# MODEL: every search is logged here. @app.admin registers it in the
# Django admin panel so you can browse/search the log at /admin.
@app.admin
class SearchQuery(models.Model):
    query = models.CharField(max_length=255)   # the search text
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return self.query

    class Meta:
        ordering = ["-created_at"]   
# HELPERS: session history
def _session_history(request):
    """Read this user's history list from their session cookie (server-side)."""
    return request.session.get("history", [])


def _add_to_history(request, q):
    """Add query to history: remove duplicates (case-insensitive), put newest
    first, keep only the last 15. .modified tells Django to save the session
    even though we only mutated a nested list."""
    h = [x for x in _session_history(request) if x.lower() != q.lower()]
    h.insert(0, q)
    request.session["history"] = h[:15]
    request.session.modified = True


def _ddg_json(url, timeout=10):
    """Fetch a URL and parse the JSON body. A custom User-Agent is required -
    DuckDuckGo rejects requests with Python's default 'Python-urllib' header."""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MiniSearch/1.0)"})
    with urlopen(req, timeout=timeout) as resp:
        return _json.loads(resp.read().decode("utf-8"))


def _parse_ddg(data):
    """Flatten DuckDuckGo's nested instant-answer JSON into simple card dicts:
    [{'title':..., 'body':..., 'url':...}, ...] that RESULTS_HTML can loop over."""
    results = []
    if data.get("Answer"):                       # direct answer box ("42")
        results.append({"title": "Answer", "body": data["Answer"], "url": ""})
    if data.get("AbstractText"):                 # the Wikipedia-style summary
        results.append({
            "title": data.get("Heading") or "Summary",
            "body": data["AbstractText"],
            "url": data.get("AbstractURL", ""),
        })
    for t in data.get("RelatedTopics", []):      # up to ~5 related topics
        if isinstance(t, dict) and t.get("Text"):
            slug = t.get("FirstURL", "").rstrip("/").split("/")[-1] or "Related"
            results.append({"title": slug, "body": t["Text"], "url": t.get("FirstURL", "")})
    return results

# ROUTE: the home page - just renders the big inline INDEX_HTML template.

@app.route("/")
def index(request):
    return render_html(INDEX_HTML, {})

# ROUTE: /search/?q=python
# 1. logs the query to the SearchQuery model (visible in /admin)
# 2. saves it to session history (visible in the clock-icon list)
# 3. calls DuckDuckGo server-side and renders the RESULTS_HTML fragment
@app.route("/search/")
def search(request):
    q = request.GET.get("q", "").strip()
    results, error = [], None

    if q:
        SearchQuery.objects.create(query=q[:255])
        _add_to_history(request, q)
        api_url = "https://api.duckduckgo.com/?" + urlencode(
            {"q": q, "format": "json", "no_html": 1, "skip_disambig": 1}
        )
        try:
            results = _parse_ddg(_ddg_json(api_url))
        except Exception as exc:
            error = str(exc)

    return render_html(RESULTS_HTML, {"results": results, "q": q, "error": error})
    
# ROUTE: /history/ - render the current session's history rows.
# /history/remove/3/ deletes one entry (index comes from the URL),
# /history/clear/ empties the whole list. Both then re-render the fragment.
@app.route("/history/")
def history(request):
    return render_html(HISTORY_HTML, {"history": _session_history(request)})


@app.route("/history/remove/<int:i>/")
def history_remove(request, i):
    h = _session_history(request)
    if 0 <= i < len(h):            # bounds check: never trust the URL
        h.pop(i)
        request.session["history"] = h
        request.session.modified = True
    return history(request)


@app.route("/history/clear/")
def history_clear(request):
    request.session["history"] = []
    return history(request)
# ROUTE: /autocomplete/?q=hello
# Proxies DuckDuckGo's autocomplete endpoint server-side and returns a plain
# JSON list of strings, e.g. ["hello world", "hello kitty", ...].
# safe=False allows JsonResponse

if __name__ == "__main__":
    app.run()
