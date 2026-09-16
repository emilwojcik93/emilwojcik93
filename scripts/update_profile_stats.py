#!/usr/bin/env python3
"""Render profile cards from public GitHub data using the authenticated gh CLI."""

import collections
import concurrent.futures
import datetime
import html
import json
import pathlib
import subprocess

USERNAME = "emilwojcik93"
ROOT = pathlib.Path(__file__).resolve().parents[1]
COLORS = ("#58a6ff", "#3fb950", "#d2a8ff", "#f0883e", "#f2cc60", "#ff7b72")


def api(endpoint, *, paginate=False):
    command = ["gh", "api", "--hostname", "github.com", endpoint]
    if paginate:
        command += ["--paginate", "--slurp"]
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=90)
    return json.loads(result.stdout)


def public_owned(repositories):
    """Fail closed for missing visibility or ownership metadata."""
    return [
        repo for repo in repositories
        if repo.get("private") is False
        and repo.get("visibility") == "public"
        and repo.get("owner", {}).get("login", "").lower() == USERNAME.lower()
    ]


def collect_snapshot(fetch=api, today=None):
    user = fetch(f"users/{USERNAME}")
    pages = fetch(f"users/{USERNAME}/repos?type=owner&per_page=100", paginate=True)
    repositories = public_owned([repo for page in pages for repo in page])
    originals = [repo for repo in repositories if repo.get("fork") is False]

    def languages(repo):
        return fetch(f"repos/{USERNAME}/{repo['name']}/languages")

    totals = collections.Counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(languages, originals):
            for language, size in result.items():
                if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                    raise ValueError("Invalid repository language byte count")
                if size:
                    totals[language] += size
    return {
        "date": today or datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
        "public_repositories": len(repositories),
        "original_repositories": len(originals),
        "stars": sum(repo["stargazers_count"] for repo in originals),
        "followers": user["followers"],
        "languages": dict(sorted(totals.items(), key=lambda item: (-item[1], item[0]))),
    }


def text(x, y, content, *, size=14, color="#e6edf3", weight=400):
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
        f'font-weight="{weight}">{html.escape(str(content))}</text>'
    )


def card(title, description, height, body, width=760):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">\n'
        f'<title id="title">{html.escape(title)}</title>\n'
        f'<desc id="desc">{html.escape(description)}</desc>\n'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        'fill="#0d1117" stroke="#30363d"/>\n'
        '<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif">\n'
        + "\n".join(body) + "\n</g>\n</svg>\n"
    )


def render_stats(snapshot, compact=False):
    metrics = [
        ("Public repositories", snapshot["public_repositories"]),
        ("Original repositories", snapshot["original_repositories"]),
        ("Stars earned", snapshot["stars"]),
        ("Followers", snapshot["followers"]),
    ]
    body = [text(24, 35, "Public GitHub snapshot", size=20, weight=600)]
    for index, (label, value) in enumerate(metrics):
        x = 24 + (index % 2) * 178 if compact else 24 + index * 183
        y = 92 + (index // 2) * 78 if compact else 92
        body += [text(x, y, f"{value:,}", size=34, color="#58a6ff", weight=600), text(x, y + 28, label)]
    if compact:
        body += [
            text(24, 229, "Original repositories and stars exclude forks.", size=12, color="#9198a1"),
            text(24, 251, f"Public data · {snapshot['date']} UTC", size=12, color="#9198a1"),
        ]
        return card("Public GitHub snapshot", "; ".join(f"{label}: {value}" for label, value in metrics), 272, body, width=380)
    body += [
        text(24, 159, "Repository total includes forks; original repositories and stars exclude forks.", size=12, color="#9198a1"),
        text(24, 181, f"Public data only · Updated {snapshot['date']} UTC", size=12, color="#9198a1"),
    ]
    return card("Public GitHub snapshot", "; ".join(f"{label}: {value}" for label, value in metrics), 202, body)


def render_languages(snapshot, compact=False):
    items = list(snapshot["languages"].items())
    total = sum(value for _, value in items)
    if len(items) > 6:
        items = items[:5] + [("Other", sum(value for _, value in items[5:]))]
    body = [text(24, 35, "Languages in public projects", size=18 if compact else 20, weight=600)]
    for index, (language, size) in enumerate(items):
        y = 73 + index * (44 if compact else 30)
        share = size / total
        bar_x, bar_y, bar_width = (24, y + 8, 332) if compact else (180, y - 12, 480)
        body += [
            text(24, y, language),
            f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="12" rx="4" fill="#21262d"/>',
            f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width * share:.2f}" height="12" rx="4" fill="{COLORS[index]}"/>',
            text(300 if compact else 680, y, f"{share:.1%}"),
        ]
    if not items:
        body.append(text(24, 75, "No public language data available."))
    footer_y = 85 + max(len(items), 1) * (44 if compact else 30)
    body += [
        text(24, footer_y, "Source bytes; public originals only." if compact else "Share of detected source bytes in owned, non-fork public repositories.", size=12, color="#9198a1"),
        text(24, footer_y + 22, f"Not a skills ranking · {snapshot['date']} UTC" if compact else f"Not a proficiency ranking · Updated {snapshot['date']} UTC", size=12, color="#9198a1"),
    ]
    description = "; ".join(f"{language}: {size / total:.1%}" for language, size in items)
    return card("Languages in public projects", description or "No language data available", footer_y + 44, body, width=380 if compact else 760)


def refresh(output_dir, fetch=api, today=None):
    # Complete every API read and render before replacing the last good cards.
    snapshot = collect_snapshot(fetch, today)
    cards = {
        "github-stats.svg": render_stats(snapshot),
        "top-languages.svg": render_languages(snapshot),
        "github-stats-mobile.svg": render_stats(snapshot, compact=True),
        "top-languages-mobile.svg": render_languages(snapshot, compact=True),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in cards.items():
        temporary = output_dir / f".{name}.tmp"
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(output_dir / name)
    return snapshot


if __name__ == "__main__":
    result = refresh(ROOT / "assets")
    print(json.dumps(result, indent=2))
