#!/usr/bin/env python3
"""
Reddit Pain Analyzer
====================
Read-only personal research tool.
Fetches top public Reddit posts for a given niche and uses AI
to surface recurring pain points, feature requests, and product opportunities.

Reddit API usage:
  - OAuth2 "script" app type (personal use, read-only scopes)
  - Never posts, votes, comments, or modifies anything
  - Respects rate limits via PRAW's built-in throttling
"""

import os
import sys
import praw
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

REDDIT = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],         # from reddit.com/prefs/apps
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    username=os.environ["REDDIT_USERNAME"],
    password=os.environ["REDDIT_PASSWORD"],
    user_agent="pain-analyzer:v1.0 (personal research script by /u/akado2010)",
    # read_only=True ensures no write actions are possible
    read_only=True,
)

GPT = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# ---------------------------------------------------------------------------
# Subreddit mapping per niche
# ---------------------------------------------------------------------------

NICHE_SUBREDDITS = {
    "default":     ["Entrepreneur", "startups", "SideProject", "indiehackers", "smallbusiness"],
    "saas":        ["SaaS", "startups", "indiehackers", "SideProject"],
    "indie":       ["indiehackers", "SideProject", "digitalnomad", "Entrepreneur"],
    "solopreneur": ["Entrepreneur", "SideProject", "indiehackers", "freelance"],
    "dev":         ["webdev", "learnprogramming", "ExperiencedDevs", "cscareerquestions"],
    "marketing":   ["marketing", "digital_marketing", "SEO", "socialmedia"],
    "ai":          ["MachineLearning", "ChatGPT", "LocalLLaMA", "ArtificialIntelligence"],
}


def get_subreddits(niche: str) -> list[str]:
    niche_lower = niche.lower()
    for key in NICHE_SUBREDDITS:
        if key in niche_lower:
            return NICHE_SUBREDDITS[key]
    return NICHE_SUBREDDITS["default"]


# ---------------------------------------------------------------------------
# Fetch posts via official Reddit API (read-only)
# ---------------------------------------------------------------------------

def fetch_top_comments(submission, limit: int = 5) -> list[str]:
    """Return top-level comments with highest score."""
    comments = []
    try:
        submission.comments.replace_more(limit=0)
        sorted_comments = sorted(
            submission.comments.list(),
            key=lambda c: getattr(c, "score", 0),
            reverse=True,
        )
        for comment in sorted_comments[:limit]:
            body = getattr(comment, "body", "")
            if len(body) > 30:
                comments.append(body[:300])
    except Exception:
        pass
    return comments


def fetch_posts(niche: str, posts_per_sub: int = 15) -> list[dict]:
    subreddits = get_subreddits(niche)
    print(f"\n🔍 Scanning subreddits: {', '.join('r/' + s for s in subreddits)}")

    posts = []
    for sub_name in subreddits:
        try:
            subreddit = REDDIT.subreddit(sub_name)
            # search() uses Reddit's official search — read-only
            results = subreddit.search(
                query=niche,
                sort="top",
                time_filter="month",
                limit=posts_per_sub,
            )
            count = 0
            for submission in results:
                if submission.score < 3:
                    continue
                top_comments = fetch_top_comments(submission)
                posts.append({
                    "title":        submission.title,
                    "selftext":     (submission.selftext or "")[:500],
                    "score":        submission.score,
                    "url":          f"https://reddit.com{submission.permalink}",
                    "subreddit":    sub_name,
                    "top_comments": top_comments,
                })
                count += 1
            print(f"  r/{sub_name}: {count} posts")
        except Exception as e:
            print(f"  ⚠️  r/{sub_name}: {e}")

    print(f"\n✅ Fetched {len(posts)} posts total\n")
    return posts


# ---------------------------------------------------------------------------
# AI analysis
# ---------------------------------------------------------------------------

def analyze(niche: str, posts: list[dict]) -> str:
    posts_text = ""
    for i, p in enumerate(posts, 1):
        posts_text += f"\n--- Post {i} (r/{p['subreddit']}, score: {p['score']}) ---\n"
        posts_text += f"Title: {p['title']}\n"
        if p["selftext"]:
            posts_text += f"Body: {p['selftext']}\n"
        if p["top_comments"]:
            posts_text += "Top comments:\n"
            posts_text += "\n".join(f"  • {c}" for c in p["top_comments"]) + "\n"

    prompt = f"""You are analyzing Reddit posts about "{niche}" to extract real user pains and needs.

Here are the posts:
{posts_text}

Produce a structured report:

## 🔥 Top Pain Points (ranked by frequency/upvotes)
List 5-8 specific pain points. For each:
- **Pain**: [clear description]
- **Evidence**: [1-2 direct quotes or post titles]
- **Frequency**: [how many posts mention this]

## 💡 Most Requested Solutions / Features
List 4-6 things people are actively asking to be built or improved.

## 😤 Common Frustrations with Existing Tools
What tools/solutions are people complaining about and why?

## 🚀 Potential Product Ideas
3-5 concrete product ideas that address the pains above.

## 📊 Audience Profile
Who exactly is posting? Level, context, goals.

Use real language from the posts. No generic advice.
"""

    print("🤖 Analyzing with GPT-4o...\n")
    response = GPT.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Save report
# ---------------------------------------------------------------------------

def save_report(niche: str, report: str, posts: list[dict]) -> str:
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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

    report = analyze(niche, posts)
    print(report)
    save_report(niche, report, posts)


if __name__ == "__main__":
    main()
