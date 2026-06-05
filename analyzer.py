#!/usr/bin/env python3
"""Reddit Pain Analyzer — finds top pains and requests in a niche."""

import os
import sys
import time
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

GPT = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

HEADERS = {"User-Agent": "pain-analyzer/1.0"}
HN_API = "https://hn.algolia.com/api/v1/search"

def reddit_get(url: str, params: dict = None) -> dict:
    """Fetch endpoint with rate limiting."""
    time.sleep(1)
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

# Subreddits to search per niche keyword — extend as needed
NICHE_SUBREDDITS = {
    "default": ["Entrepreneur", "startups", "SideProject", "indiehackers", "smallbusiness"],
    "saas": ["SaaS", "startups", "indiehackers", "SideProject"],
    "indie": ["indiehackers", "SideProject", "digitalnomad", "Entrepreneur"],
    "solopreneur": ["Entrepreneur", "SideProject", "indiehackers", "freelance"],
    "dev": ["webdev", "learnprogramming", "ExperiencedDevs", "cscareerquestions"],
    "marketing": ["marketing", "digital_marketing", "SEO", "socialmedia"],
    "ai": ["artificial", "MachineLearning", "ChatGPT", "LocalLLaMA", "ArtificialIntelligence"],
}


def get_subreddits(niche: str) -> list[str]:
    niche_lower = niche.lower()
    for key in NICHE_SUBREDDITS:
        if key in niche_lower:
            return NICHE_SUBREDDITS[key]
    return NICHE_SUBREDDITS["default"]


def fetch_posts(niche: str, limit: int = 60) -> list[dict]:
    print(f"\n🔍 Searching Hacker News for: '{niche}'")

    posts = []

    # Search stories (Ask HN, Show HN, regular posts)
    for tag in ["story", "ask_hn", "show_hn"]:
        try:
            params = {
                "query": niche,
                "tags": tag,
                "hitsPerPage": limit // 3,
                "numericFilters": "points>5",
            }
            data = reddit_get(HN_API, params=params)
            hits = data.get("hits", [])
            print(f"  [{tag}]: {len(hits)} posts")

            for h in hits:
                posts.append({
                    "title": h.get("title", ""),
                    "selftext": (h.get("story_text") or "")[:500],
                    "score": h.get("points", 0),
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "subreddit": tag,
                    "top_comments": [],
                })
        except Exception as e:
            print(f"  ⚠️  {tag}: {e}")

    # Also grab top comments mentioning the niche
    try:
        params = {"query": niche, "tags": "comment", "hitsPerPage": 20, "numericFilters": "points>3"}
        data = reddit_get(HN_API, params=params)
        for h in data.get("hits", []):
            text = h.get("comment_text", "") or ""
            if len(text) > 50:
                posts.append({
                    "title": f"[Comment] {text[:100]}...",
                    "selftext": text[:500],
                    "score": h.get("points", 0),
                    "url": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "subreddit": "comment",
                    "top_comments": [],
                })
        print(f"  [comments]: {len(data.get('hits', []))} relevant comments")
    except Exception as e:
        print(f"  ⚠️  comments: {e}")

    print(f"\n✅ Fetched {len(posts)} items\n")
    return posts


def analyze_with_claude(niche: str, posts: list[dict]) -> str:
    posts_text = ""
    for i, p in enumerate(posts, 1):
        posts_text += f"\n--- Post {i} (r/{p['subreddit']}, score: {p['score']}) ---\n"
        posts_text += f"Title: {p['title']}\n"
        if p["selftext"]:
            posts_text += f"Body: {p['selftext']}\n"
        if p["top_comments"]:
            posts_text += "Top comments:\n" + "\n".join(f"  • {c}" for c in p["top_comments"]) + "\n"

    prompt = f"""You are analyzing Reddit posts about "{niche}" to extract real user pains and needs.

Here are the posts:
{posts_text}

Produce a structured report with these sections:

## 🔥 Top Pain Points (ranked by frequency/upvotes)
List 5-8 specific pain points. For each:
- **Pain**: [clear description]
- **Evidence**: [1-2 example quotes or post titles]
- **Frequency**: [how many posts mention this]

## 💡 Most Requested Solutions / Features
List 4-6 things people are actively looking for or asking to be built.

## 😤 Common Frustrations with Existing Tools
What tools/solutions are people complaining about and why?

## 🚀 Potential Product Ideas
Based on the pains above, suggest 3-5 product/feature ideas that could address them.

## 📊 Audience Profile
Who exactly is complaining? Their level, context, goals.

Be specific and use real language from the posts. No generic advice.
"""

    print("🤖 Analyzing with GPT-4o... (Hacker News data)\n")
    response = GPT.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def save_report(niche: str, report: str, posts: list[dict]):
    slug = niche.lower().replace(" ", "_")
    filename = f"report_{slug}.md"
    with open(filename, "w") as f:
        f.write(f"# Reddit Pain Analysis: {niche}\n\n")
        f.write(f"*Analyzed {len(posts)} posts from Reddit*\n\n")
        f.write(report)
        f.write("\n\n---\n## 🔗 Source Posts\n")
        for p in sorted(posts, key=lambda x: x["score"], reverse=True)[:15]:
            f.write(f"- [{p['title'][:80]}]({p['url']}) — score: {p['score']}\n")
    print(f"\n💾 Report saved to: {filename}")
    return filename


def main():
    niche = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Enter niche/topic: ").strip()
    if not niche:
        print("Usage: python analyzer.py <niche>")
        sys.exit(1)

    print(f"\n🎯 Analyzing Reddit pains for: '{niche}'")

    posts = fetch_posts(niche)
    if not posts:
        print("No posts found. Try a different niche.")
        sys.exit(1)

    report = analyze_with_claude(niche, posts)
    print(report)

    save_report(niche, report, posts)


if __name__ == "__main__":
    main()
