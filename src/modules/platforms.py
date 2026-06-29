# ──────────────────────────────────────────────────────────
# GHOST — Global Heuristic OSINT Search Tool
# Pseudo checker sur 50+ plateformes
# ──────────────────────────────────────────────────────────

PLATFORMS = {
    #  === SOCIAL MEDIA ===
    "twitter": {
        "url": "https://twitter.com/{username}",
        "type": "social",
    },
    "reddit": {
        "url": "https://www.reddit.com/user/{username}",
        "type": "social",
    },
    "instagram": {
        "url": "https://www.instagram.com/{username}",
        "type": "social",
    },
    "tiktok": {
        "url": "https://www.tiktok.com/@{username}",
        "type": "social",
    },
    "youtube": {
        "url": "https://www.youtube.com @{username}",
        "type": "social",
    },
    "twitch": {
        "url": "https://www.twitch.tv/{username}",
        "type": "social",
    },
    "pinterest": {
        "url": "https://www.pinterest.com/{username}",
        "type": "social",
    },
    "tumblr": {
        "url": "https://{username}.tumblr.com",
        "type": "social",
    },
    "bluesky": {
        "url": "https://bsky.app/profile/{username}.bsky.social",
        "type": "social",
    },
    "mastodon": {
        "url": "https://mastodon.social @{username}",
        "type": "social",
    },
    "gab": {
        "url": "https://gab.com/{username}",
        "type": "social",
    },
    "odysee": {
        "url": "https://odysee.com/@{username}",
        "type": "social",
    },
    "rumble": {
        "url": "https://rumble.com/user/{username}",
        "type": "social",
    },
    "vk": {
        "url": "https://vk.com/{username}",
        "type": "social",
    },
    "snapchat": {
        "url": "https://www.snapchat.com/add/{username}",
        "type": "social",
    },
    "clubhouse": {
        "url": "https://www.clubhouse.com/@{username}",
        "type": "social",
    },
    "threads": {
        "url": "https://www.threads.net/@{username}",
        "type": "social",
    },
    "parler": {
        "url": "https://parler.com/{username}",
        "type": "social",
    },
    "truth_social": {
        "url": "https://truthsocial.com @{username}",
        "type": "social",
    },

    # === CODING / DEV ===
    "github": {
        "url": "https://api.github.com/users/{username}",
        "type": "coding",
        "api": True,
    },
    "gitlab": {
        "url": "https://gitlab.com/{username}",
        "type": "coding",
    },
    "bitbucket": {
        "url": "https://bitbucket.org/{username}",
        "type": "coding",
    },
    "devto": {
        "url": "https://dev.to/{username}",
        "type": "coding",
    },
    "hashnode": {
        "url": "https://hashnode.com @{username}",
        "type": "coding",
    },
    "stackoverflow": {
        "url": "https://stackoverflow.com/users/filter?search={username}",
        "type": "coding",
    },
    "codepen": {
        "url": "https://codepen.io/{username}",
        "type": "coding",
    },
    "replit": {
        "url": "https://replit.com/@{username}",
        "type": "coding",
    },
    "keybase": {
        "url": "https://keybase.io/{username}",
        "type": "coding",
    },

    # === GAMING ===
    "steam": {
        "url": "https://steamcommunity.com/id/{username}",
        "type": "gaming",
    },
    "steam_community": {
        "url": "https://steamcommunity.com/search/UserFiles?username={username}",
        "type": "gaming",
    },
    "epic_games": {
        "url": "https://www.epicgames.com/{username}",
        "type": "gaming",
    },
    "chess": {
        "url": "https://www.chess.com/member/{username}",
        "type": "gaming",
    },
    "lichess": {
        "url": "https://lichess.org/@/{username}",
        "type": "gaming",
    },
    "roblox": {
        "url": "https://www.roblox.com/user.aspx?username={username}",
        "type": "gaming",
    },
    "vrchat": {
        "url": "https://vrchat.com/home/user/{username}",
        "type": "gaming",
    },

    # === MEDIA / CREATORS ===
    "vine": {
        "url": "https://webcache.googleusercontent.com/search?q=vine.co/{username}",
        "type": "media",
    },
    "vimeo": {
        "url": "https://vimeo.com/{username}",
        "type": "media",
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com/{username}",
        "type": "media",
    },
    "soundcloud": {
        "url": "https://soundcloud.com/{username}",
        "type": "media",
    },
    "spotify": {
        "url": "https://open.spotify.com/user/{username}",
        "type": "media",
    },
    "lastfm": {
        "url": "https://www.last.fm/user/{username}",
        "type": "media",
    },
    "flickr": {
        "url": "https://www.flickr.com/photos/{username}",
        "type": "media",
    },
    "patreon": {
        "url": "https://www.patreon.com/{username}",
        "type": "media",
    },
    "substack": {
        "url": "https://{username}.substack.com",
        "type": "media",
    },
    "medium": {
        "url": "https://medium.com @{username}",
        "type": "media",
    },
    "buymeacoffee": {
        "url": "https://www.buymeacoffee.com/{username}",
        "type": "media",
    },
    "ko-fi": {
        "url": "https://ko-fi.com/{username}",
        "type": "media",
    },

    # === CRYPTO / FINANCE ===
    "etherscan": {
        "url": "https://etherscan.io/address/{username}",
        "type": "crypto",
    },
    "blockchain_com": {
        "url": "https://www.blockchain.com/btc/address/{username}",
        "type": "crypto",
    },
    "coinbase": {
        "url": "https://www.coinbase.com/{username}",
        "type": "crypto",
    },
    "tradingview": {
        "url": "https://www.tradingview.com/u/{username}",
        "type": "crypto",
    },

    # === FORUMS / CHANS ===
    "4chan": {
        "url": "https://archive.4plebs.org/pol/?text={username}",
        "type": "forum",
    },
    "8kun": {
        "url": "https://8kun.top/index.html#search={username}",
        "type": "forum",
    },
    "kilid": {
        "url": "https://www.kilid.com/profile/{username}",
        "type": "forum",
    },
    "quora": {
        "url": "https://www.quora.com/profile/{username}",
        "type": "forum",
    },
    "hackernews": {
        "url": "https://news.ycombinator.com/user?id={username}",
        "type": "forum",
    },

    # === PRO / BUSINESS ===
    "linkedin": {
        "url": "https://www.linkedin.com/in/{username}",
        "type": "pro",
    },
    "aboutme": {
        "url": "https://about.me/{username}",
        "type": "pro",
    },
    "linktree": {
        "url": "https://linktr.ee/{username}",
        "type": "pro",
    },
    "behance": {
        "url": "https://www.behance.net/{username}",
        "type": "pro",
    },
    "dribbble": {
        "url": "https://dribbble.com/{username}",
        "type": "pro",
    },
    "producthunt": {
        "url": "https://www.producthunt.com @{username}",
        "type": "pro",
    },
    "gravatar": {
        "url": "https://en.gravatar.com/{username}",
        "type": "pro",
    },

    # === DATING ===
    "tinder": {
        "url": "https://tinder.com/@{username}",
        "type": "dating",
    },
    "okcupid": {
        "url": "https://www.okcupid.com/profile/{username}",
        "type": "dating",
    },
    "bumble": {
        "url": "https://bumble.com/@{username}",
        "type": "dating",
    },

    # === MUSIC/ENTERTAINMENT ===
    "discord_lookup": {
        "url": "https://discordlookup.com/user/{username}",
        "type": "discord",
    },
    "discord_id": {
        "url": "https://discord.com/users/{username}",
        "type": "discord",
    },
    "telegram": {
        "url": "https://t.me/{username}",
        "type": "telegram",
    },
}

# Catégories pour filtrer
CATEGORIES = {
    "social": "📱 Social Media",
    "coding": "💻 Coding / Dev",
    "gaming": "🎮 Gaming",
    "media": "🎬 Media / Creators",
    "crypto": "₿ Crypto / Finance",
    "forum": "💬 Forums / Chans",
    "pro": "💼 Pro / Business",
    "dating": "❤️ Dating",
    "discord": "🎙 Discord",
    "telegram": "✈️ Telegram",
}
