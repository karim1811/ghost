# GHOST — Known false-positive detection patterns
# Per-platform "not found" indicators

NOT_FOUND_INDICATORS = {
    # Social
    "twitter": ["this account doesn’t exist", "this account doesn't exist", "suspended"],
    "instagram": ["sorry, this page isn't available", "page not found"],
    "tiktok": ["Couldn't find this account", "couldn't find this account"],
    "youtube": ["404", "this page isn't available"],
    "twitch": ["about_anonymous", "not found"],
    "pinterest": ["sorry, this page", "not found"],
    "tumblr": ["there's nothing here", "not found"],
    "bluesky": ["not found"],
    "mastodon": ["the page you are looking", "404"],
    "odysee": ["content not found", "404"],
    "rumble": ["404"],
    "reddit": ["page not found", "this subreddit was banned", "this subreddit has been banned"],
    "gab": ["page not found", "404"],
    "threads": ["the link may be broken", "not found"],

    # Coding
    "github": ["404"],
    "gitlab": ["404", "not found"],
    "bitbucket": ["404", "not found"],
    "devto": ["404", "not found"],
    "hashnode": ["404", "not found"],
    "codepen": ["404"],
    "replit": ["404", "this user was not found"],
    "keybase": ["404", "not found"],

    # Gaming
    "steam": ["the specified profile could not be found", "this user has not yet"],
    "chess": ["404"],
    "lichess": ["page not found", "404"],
    "roblox": ["page cannot be found", "404"],
    "vrchat": ["404"],

    # Media
    "vimeo": ["404", "we couldn't find that page"],
    "dailymotion": ["404", "page not found"],
    "soundcloud": ["404"],
    "spotify": ["sorry, we couldn't find that page", "something went wrong"],
    "lastfm": ["404"],
    "flickr": ["404"],
    "patreon": ["404", "beep... beep... nothing here"],
    "substack": ["not found", "404"],
    "medium": ["404"],
    "buymeacoffee": ["404"],
    "ko-fi": ["404", "we could not find"],

    # Crypto
    "etherscan": ["error", "not found"],
    "blockchain_com": ["page not found", "404"],
    "coinbase": ["404"],
    "tradingview": ["404"],

    # Forums
    "4chan": ["404"],
    "8kun": ["404"],
    "quora": ["404"],
    "hackernews": ["no such user", "404"],

    # Pro
    "linkedin": ["page not found", "404"],
    "aboutme": ["404", "page not found"],
    "linktree": ["404", "not found"],
    "behance": ["404"],
    "dribbble": ["404"],
    "producthunt": ["404"],
    "gravatar": ["not found"],

    # Dating
    "tinder": ["404", "page not found"],
    "okcupid": ["page not found", "404"],
    "bumble": ["404"],

    # Discord / Telegram
    "discord_lookup": ["not found", "404"],
    "discord_id": ["404"],
    "telegram": ["page not found"],
}

# These platforms return 200 for non-existent profiles (hard to detect)
REQUIRES_GET_CHECK = [
    "twitter", "x", "instagram", "tiktok", "pinterest", "odysee",
    "rumble", "gab", "bluesky", "tumblr", "threads", "parler",
    "vk", "snapchat", "clubhouse",

    "aboutme", "linktree", "behance", "dribbble", "producthunt",

    "tinder", "okcupid", "bumble",
    "etherscan", "blockchain_com", "coinbase",

    "discord_lookup", "discord_id", "telegram",
    "replit", "codepen",
]
