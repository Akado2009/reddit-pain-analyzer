# Reddit Pain Analyzer

A personal, read-only research CLI tool that fetches public Reddit posts and uses AI to summarize user pain points and market needs within a given niche.

## What it does

- Reads **public Reddit posts** via the official Reddit API (OAuth, read-only, no writes)
- Searches specified subreddits for a given topic/niche
- Extracts post titles and body text
- Uses an LLM to cluster and summarize pain points, feature requests, and frustrations
- Saves a structured Markdown report locally

**No posts, comments, or messages are ever created.** The script is fully read-only.

## Usage

```bash
python analyzer.py "indie hacking"
python analyzer.py "SaaS pricing"
python analyzer.py "solopreneur"
```

## Output example

```
## 🔥 Top Pain Points
1. Marketing is hard for solo builders...
2. Freemium conversion is unclear...

## 🚀 Potential Product Ideas
1. ...
```

## Subreddits accessed (read-only)

- r/Entrepreneur
- r/startups
- r/SideProject
- r/indiehackers
- r/smallbusiness
- r/webdev

All subreddits are public. The tool never posts, votes, comments, or interacts with any user.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your Reddit API credentials and OpenAI key to .env
python analyzer.py "your niche"
```

## Privacy

- No user data is stored beyond local Markdown files
- No data is shared or uploaded anywhere
- Script runs entirely on the user's local machine
