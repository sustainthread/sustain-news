import html
import feedparser
import json
import os
from datetime import datetime, timedelta
import hashlib
import re
from urllib.parse import urlparse
import time

# ==================== CONFIGURATION ====================

# RSS FEEDS ORGANIZED BY TIER FOR BETTER FILTERING
RSS_FEEDS_BY_TIER = {
    # TIER 1: Dedicated sustainability sources (lowest threshold)
    "tier1_sustainability": [
        'https://www.greenbiz.com/rss',
        'https://feeds.feedburner.com/SustainableBrands',
        'https://www.triplepundit.com/feed/',
        'https://www.ecotextile.com/rss',
        'https://www.csrwire.com/rss',  # NEW: Corporate social responsibility
        'https://www.esgtoday.com/feed/',  # NEW: ESG focused
    ],
    
    # TIER 2: Environment & climate focused (moderate threshold)
    "tier2_environment": [
        'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml',
        'https://www.theguardian.com/uk/environment/rss',
        'https://feeds.npr.org/1005/rss.xml',
        'https://www.sciencedaily.com/rss/earth_climate/environment.xml',
        'https://insideclimatenews.org/feed/',  # NEW: Climate focused
        'https://e360.yale.edu/feed',  # NEW: Yale Environment
        'https://www.climatechangenews.com/feed/',  # NEW: Specialized
    ],
    
    # TIER 3: Fashion & sustainability (industry specific)
    "tier3_fashion": [
        'https://www.businessoffashion.com/rss',
        'https://sourcingjournal.com/feed/',
        'https://www.voguebusiness.com/feed/rss',
        'https://goodonyou.eco/feed/',  # NEW: Ethical fashion
        'https://www.commonobjective.co/articles/feed',  # NEW: Sustainable fashion
    ],
    
    # TIER 4: General news with sustainability sections (highest threshold)
    "tier4_general_news": [
        'https://www.aljazeera.com/xml/rss/all.xml?tag=Climate',  # UPDATED: Climate specific
        'https://feeds.reuters.com/reuters/environment',  # Specific environment feed
        'https://www.thehindu.com/topic/sustainability/feeder/default.rss',  # UPDATED: Specific topic
        'https://www.euronews.com/rss?format=mrss&level=theme&name=green',  # Green specific
        'https://feeds.reuters.com/reuters/scienceNews',
    ]
}

# TIER CONFIGURATION - Different thresholds for different source types
TIER_CONFIG = {
    "tier1_sustainability": {
        "threshold": 2,      # Lower threshold for dedicated sources
        "max_articles": 10,  # Get more from these trusted sources
        "bonus_score": 3,    # Bonus for being a sustainability-focused source
    },
    "tier2_environment": {
        "threshold": 3,
        "max_articles": 8,
        "bonus_score": 2,
    },
    "tier3_fashion": {
        "threshold": 3,
        "max_articles": 6,
        "bonus_score": 2,
    },
    "tier4_general_news": {
        "threshold": 5,      # Highest threshold - must be very relevant
        "max_articles": 4,   # Limit articles from general news
        "bonus_score": 0,    # No bonus for general news
    }
}

# ENHANCED KEYWORD SYSTEM WITH CONTEXTUAL PHRASES
KEYWORD_CATEGORIES = {
    # Environmental action (strong indicators)
    "environmental_action": [
        "carbon reduction", "emissions target", "renewable energy", "clean energy",
        "climate action", "net zero", "carbon neutral", "decarbonization",
        "waste management", "plastic pollution", "biodiversity loss",
        "circular economy", "sustainable development", "green technology",
    ],
    
    # ESG & Corporate reporting (strong indicators)
    "esg_reporting": [
        "esg report", "sustainability report", "corporate sustainability",
        "csr report", "sustainability disclosure", "esg metrics",
        "sbti", "science based targets", "tcfd", "sasb", "csrd",
        "scope 3 emissions", "carbon footprint", "esg rating",
    ],
    
    # Fashion sustainability (strong indicators)
    "fashion_sustainability": [
        "sustainable fashion", "ethical fashion", "circular fashion",
        "organic cotton", "recycled textile", "eco-friendly apparel",
        "slow fashion", "ethical manufacturing", "sustainable textile",
        "fashion waste", "textile recycling", "upcycled clothing",
    ],
    
    # Weaker single keywords (still relevant but need context)
    "general_keywords": [
        "sustainability", "sustainable", "environment", "green",
        "climate", "eco-friendly", "conservation", "pollution",
    ]
}

# STRONG REJECTION RULES - Immediate exclusion
REJECTION_RULES = [
    # Pattern: (check_type, keywords, [optional context checks])
    ("any", ["election", "trump", "biden", "vote", "campaign", "senate", "congress"]),
    ("any", ["football", "soccer", "basketball", "nfl", "nba", "sports", "olympics"]),
    ("any", ["celebrity", "movie", "hollywood", "oscar", "netflix", "entertainment"]),
    ("any", ["crime", "murder", "shooting", "arrest", "lawsuit", "investigation"]),
    ("any", ["crypto", "bitcoin", "ethereum", "blockchain", "nft"]),
    ("any", ["recipe", "cooking", "restaurant", "food", "diet"]),
    
    # Contextual rejection: "green" in financial context
    ("context", ["green", "sustainable"], ["stock", "profit", "dividend", "earnings", "market", "trading"]),
    
    # Contextual rejection: "policy" in political context
    ("context", ["policy", "regulation"], ["government", "administration", "white house", "senate"]),
    
    # New rule: Reject articles focused on armed conflicts or specific humanitarian crises
    ("any", ["gaza", "ukraine", "war", "humanitarian crisis", "genocide"]),
    
    # New rule: Reject articles that are purely animal photo galleries or non-substantive wildlife features
    ("context", ["wildlife", "photograph"], ["week in", "gallery", "photo", "picture of"]),
    
    # New rule: Reject obscure scientific studies unrelated to environment/sustainability
    ("context", ["study", "scientists"], ["monogam", "human behavior", "league table"]),
]

# NEGATIVE KEYWORDS (strong penalty)
NEGATIVE_KEYWORDS = [
    "quarterly earnings", "stock price", "market share", "profit growth",
    "investment returns", "financial results", "economic growth",
    "political party", "election results", "campaign trail",
    "sports team", "championship game", "player contract",
    "movie review", "box office", "celebrity gossip",
     # New general negative keywords
    "obituary", "died", "death of", "in memoriam", "photo gallery", "this week in",
]

# Map domains to proper source names
SOURCE_NAME_MAP = {
    'bbci.co.uk': 'BBC',
    'nytimes.com': 'New York Times',
    'theguardian.com': 'The Guardian',
    'npr.org': 'NPR',
    'sciencedaily.com': 'Science Daily',
    'businessoffashion.com': 'Business of Fashion',
    'ecotextile.com': 'Ecotextile',
    'sourcingjournal.com': 'Sourcing Journal',
    'fashionunited.com': 'Fashion United',
    'voguebusiness.com': 'Vogue Business',
    'greenbiz.com': 'GreenBiz',
    'feedburner.com': 'Sustainable Brands',
    'triplepundit.com': 'Triple Pundit',
    'aljazeera.com': 'Al Jazeera',
    'dw.com': 'Deutsche Welle',
    'france24.com': 'France 24',
    'thehindu.com': 'The Hindu',
    'euronews.com': 'Euronews',
    'reuters.com': 'Reuters',
    'csrwire.com': 'CSRWire',
    'esgtoday.com': 'ESG Today',
    'insideclimatenews.org': 'Inside Climate News',
    'climatechangenews.com': 'Climate Change News',
    'goodonyou.eco': 'Good On You',
    'commonobjective.co': 'Common Objective',
}

# ==================== NEWS AGGREGATOR CLASS ====================

class NewsAggregator:
    def __init__(self):
        self.articles = []
        self.stats = {
            "total_fetched": 0,
            "rejected_by_rules": 0,
            "rejected_by_score": 0,
            "accepted_by_tier": {tier: 0 for tier in RSS_FEEDS_BY_TIER.keys()}
        }
        
    def get_domain_name(self, url):
        """Extract domain name from URL"""
        return urlparse(url).netloc
    
    def get_proper_source_name(self, feed_url, entry):
        """Get proper source name from domain mapping"""
        domain = self.get_domain_name(feed_url)
        
        for key, name in SOURCE_NAME_MAP.items():
            if key in domain:
                return name
        
        # Default: clean up domain name
        clean_name = domain.replace('www.', '').split('.')[0]
        return clean_name.title()
    
    def get_published_time(self, entry):
        """Extract publication time from RSS entry"""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
        return None
    
    def get_clean_description(self, entry):
    """Extract and clean description"""
    description = ""
    
    if hasattr(entry, 'description'):
        description = entry.description
    elif hasattr(entry, 'summary'):
        description = entry.summary

    # Decode HTML entities (e.g. &#8230;) and remove HTML tags
    clean_desc = html.unescape(description)
    clean_desc = re.sub('<[^<]+?>', '', clean_desc)

    # Remove publisher-added truncation markers
    clean_desc = re.sub(r'\[\s*…\s*\]|\[\s*\.\.\.\s*\]', '', clean_desc).strip()

    # Limit length for safety
    if len(clean_desc) > 200:
        if '.' in clean_desc[:150]:
            sentences = clean_desc.split('.')
            if len(sentences[0]) < 150:
                clean_desc = sentences[0] + '.'
            else:
                clean_desc = clean_desc[:147] + '...'
        else:
            clean_desc = clean_desc[:197] + '...'

    return clean_desc.strip()
    
    def should_reject_article(self, title, description):
        """Check if article should be immediately rejected"""
        content = f"{title} {description}".lower()
        
        for rule_type, keywords, *extra in REJECTION_RULES:
            if rule_type == "any":
                # Reject if ANY of these keywords appear
                if any(keyword.lower() in content for keyword in keywords):
                    return True, f"Rejected by {keywords[0]} rule"
            
            elif rule_type == "context" and extra:
                # Check contextual rejection
                main_words, forbidden_words = keywords, extra[0]
                has_main = any(word.lower() in content for word in main_words)
                has_forbidden = any(word.lower() in content for word in forbidden_words)
                
                if has_main and has_forbidden:
                    return True, f"Rejected by contextual rule: {main_words[0]} + {forbidden_words[0]}"
        
        return False, ""
    
    def calculate_relevance_score(self, title, description, source_tier):
        """Calculate enhanced relevance score with contextual analysis"""
        content = f"{title} {description}".lower()
        score = 0
        
        # ===== POSITIVE SCORING =====
        
        # 1. Strong phrase matches (environmental action)
        for phrase in KEYWORD_CATEGORIES["environmental_action"]:
            if phrase.lower() in content:
                score += 4  # Strong bonus for specific phrases
        
        # 2. ESG reporting phrases
        for phrase in KEYWORD_CATEGORIES["esg_reporting"]:
            if phrase.lower() in content:
                score += 4
        
        # 3. Fashion sustainability phrases
        for phrase in KEYWORD_CATEGORIES["fashion_sustainability"]:
            if phrase.lower() in content:
                score += 3
        
        # 4. General keywords (weaker matches)
        for keyword in KEYWORD_CATEGORIES["general_keywords"]:
            if keyword.lower() in content:
                score += 1
        
        # 5. Check for multiple sustainability indicators
        sustainability_indicators = 0
        all_keywords = []
        for category in KEYWORD_CATEGORIES.values():
            all_keywords.extend(category)
        
        for keyword in all_keywords:
            if keyword.lower() in content:
                sustainability_indicators += 1
        
        if sustainability_indicators >= 3:
            score += 3  # Bonus for multiple sustainability mentions
        elif sustainability_indicators >= 2:
            score += 2
        
        # ===== NEGATIVE SCORING =====
        
        # Strong penalty for negative keywords
        for phrase in NEGATIVE_KEYWORDS:
            if phrase.lower() in content:
                score -= 5
        
        # ===== CONTEXTUAL CHECKS =====
        
        # Check if sustainability terms are in the TITLE (stronger indicator)
        title_lower = title.lower()
        title_sustainability_terms = 0
        for category in KEYWORD_CATEGORIES.values():
            for keyword in category:
                if keyword.lower() in title_lower:
                    title_sustainability_terms += 1
                    score += 2  # Extra bonus for title mention
        
        # ===== TIER BONUS =====
        
        # Add tier-specific bonus
        tier_config = TIER_CONFIG.get(source_tier, {})
        score += tier_config.get("bonus_score", 0)
        
        # ===== RECENCY BONUS =====
        # (Applied later when we have publish date)
        
        return max(0, score)
    
    def get_source_tier(self, feed_url):
        """Determine which tier a feed belongs to"""
        for tier, feeds in RSS_FEEDS_BY_TIER.items():
            if feed_url in feeds:
                return tier
        
        # Default to general news if not found
        return "tier4_general_news"
    
    def fetch_rss_feeds(self):
        """Fetch news from RSS feeds with tier-based filtering"""
        print("📡 Fetching from RSS feeds...\n")
        
        for tier_name, feed_list in RSS_FEEDS_BY_TIER.items():
            print(f"🔹 Processing {tier_name.replace('_', ' ').title()} feeds...")
            
            tier_config = TIER_CONFIG[tier_name]
            articles_from_tier = 0
            
            for feed_url in feed_list:
                try:
                    print(f"  Fetching: {self.get_domain_name(feed_url)}", end="")
                    
                    # Add delay to be respectful to servers
                    time.sleep(0.5)
                    
                    feed = feedparser.parse(feed_url)
                    
                    if feed.bozo:
                        print(" ❌ (Feed error)")
                        continue
                    
                    articles_from_feed = 0
                    max_articles = min(tier_config["max_articles"], len(feed.entries))
                    
                    for entry in feed.entries[:max_articles]:
                        # Skip old articles (older than 7 days)
                        published_time = self.get_published_time(entry)
                        if published_time and published_time < (datetime.now() - timedelta(days=7)):
                            continue
                        
                        title = entry.title if hasattr(entry, 'title') else "No title"
                        description = self.get_clean_description(entry)
                        
                        # 1. Check for immediate rejection
                        should_reject, reason = self.should_reject_article(title, description)
                        if should_reject:
                            self.stats["rejected_by_rules"] += 1
                            continue
                        
                        # 2. Calculate relevance score
                        relevance_score = self.calculate_relevance_score(
                            title, description, tier_name
                        )
                        
                        # 3. Add recency bonus if article is relevant
                        if relevance_score > 0 and published_time:
                            days_old = (datetime.now() - published_time).days
                            if days_old == 0:
                                relevance_score += 2  # Today's news
                            elif days_old <= 2:
                                relevance_score += 1  # Last 2 days
                        
                        # 4. Apply tier-specific threshold
                        if relevance_score >= tier_config["threshold"]:
                            article = {
                                'title': title,
                                'description': description,
                                'url': entry.link if hasattr(entry, 'link') else '',
                                'publishedAt': published_time.isoformat() if published_time else datetime.now().isoformat(),
                                'source': self.get_proper_source_name(feed_url, entry),
                                'content': description[:200],
                                'relevance_score': relevance_score,
                                'source_tier': tier_name,
                                'api_source': 'rss',
                            }
                            
                            self.articles.append(article)
                            articles_from_feed += 1
                            articles_from_tier += 1
                            self.stats["total_fetched"] += 1
                        else:
                            self.stats["rejected_by_score"] += 1
                    
                    print(f" ✅ ({articles_from_feed} articles)")
                    
                except Exception as e:
                    print(f" ❌ Error: {str(e)[:50]}...")
                    continue
            
            self.stats["accepted_by_tier"][tier_name] = articles_from_tier
            print(f"  Total from this tier: {articles_from_tier} articles\n")
    
    def deduplicate_articles(self):
        """Remove duplicate articles based on URL and title similarity"""
        print("🔄 Deduplicating articles...")
        
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in self.articles:
            url = article.get('url', '')
            title = article.get('title', '').lower().strip()
            
            # Normalize URL
            url_normalized = url.split('?')[0].split('#')[0]
            
            # Create hash for comparison
            url_hash = hashlib.md5(url_normalized.encode()).hexdigest() if url_normalized else ''
            title_hash = hashlib.md5(title.encode()).hexdigest() if title else ''
            
            if url_hash not in seen_urls and title_hash not in seen_titles:
                seen_urls.add(url_hash)
                seen_titles.add(title_hash)
                unique_articles.append(article)
        
        removed = len(self.articles) - len(unique_articles)
        print(f"✅ Removed {removed} duplicates")
        self.articles = unique_articles
    
    def process_articles(self):
        """Process and analyze articles"""
        print("\n🔧 Processing articles...")
        
        # Sort by relevance score and date
        self.articles.sort(key=lambda x: (x['relevance_score'], x['publishedAt']), reverse=True)
        
        # Show statistics
        print(f"📊 Total articles after filtering: {len(self.articles)}")
        print(f"📊 Rejected by rules: {self.stats['rejected_by_rules']}")
        print(f"📊 Rejected by score: {self.stats['rejected_by_score']}")
        
        print("\n📈 Articles by tier:")
        for tier, count in self.stats["accepted_by_tier"].items():
            tier_name = tier.replace('_', ' ').title()
            print(f"   {tier_name}: {count} articles")
        
        # Show score distribution
        score_counts = {}
        for article in self.articles:
            score = article['relevance_score']
            score_counts[score] = score_counts.get(score, 0) + 1
        
        print("\n📊 Score distribution:")
        for score, count in sorted(score_counts.items(), reverse=True):
            print(f"   Score {score}: {count} articles")
        
        # Show top articles
        top_articles = [a for a in self.articles if a['relevance_score'] >= 8][:5]
        if top_articles:
            print("\n🏆 Top relevant articles:")
            for i, article in enumerate(top_articles, 1):
                print(f"   {i}. {article['title'][:80]}...")
                print(f"      Score: {article['relevance_score']} | Source: {article['source']} | Tier: {article['source_tier']}")
        
        # Show potential false positives (high scores from general news)
        general_high_scores = [
            a for a in self.articles 
            if a['source_tier'] == 'tier4_general_news' and a['relevance_score'] >= 8
        ]
        
        if general_high_scores:
            print(f"\n⚠️  Note: {len(general_high_scores)} high-scoring articles from general news sources")
            print("   Review these for potential false positives.")
    
    def save_articles(self):
        """Save articles to JSON files - compatible with current frontend"""
        print("\n💾 Saving articles...")
        
        # Format compatible with your current frontend
        frontend_data = {
            'status': 'ok',
            'totalResults': len(self.articles),
            'articles': [
                {
                    'source': {'name': article['source']},
                    'author': article['source'],
                    'title': article['title'],
                    'description': article['description'],
                    'url': article['url'],
                    'publishedAt': article['publishedAt'],
                    'content': article['content'][:200] if article['content'] else article['description'][:200]
                }
                for article in self.articles[:100]  # Limit to 100 for frontend
            ]
        }
        
        # Save to news.json
        with open('news.json', 'w', encoding='utf-8') as f:
            json.dump(frontend_data, f, indent=2, ensure_ascii=False)
        
        # Also save detailed version for debugging
        detailed_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_articles': len(self.articles),
                'stats': self.stats
            },
            'articles': self.articles
        }
        
        with open('news_detailed.json', 'w', encoding='utf-8') as f:
            json.dump(detailed_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(self.articles)} articles to news.json")
        print("✅ Saved detailed data to news_detailed.json for debugging")
    
    def run_health_check(self):
        """Quick health check of RSS feeds"""
        print("🏥 Running RSS feed health check...\n")
        
        healthy_feeds = []
        problematic_feeds = []
        
        for tier_name, feed_list in RSS_FEEDS_BY_TIER.items():
            for feed_url in feed_list[:3]:  # Check first 3 from each tier
                try:
                    feed = feedparser.parse(feed_url)
                    if feed.bozo:
                        problematic_feeds.append((feed_url, "Parse error"))
                    elif len(feed.entries) == 0:
                        problematic_feeds.append((feed_url, "No entries"))
                    else:
                        healthy_feeds.append(feed_url)
                except Exception as e:
                    problematic_feeds.append((feed_url, str(e)))
        
        print(f"✅ Healthy feeds: {len(healthy_feeds)}")
        print(f"⚠️  Problematic feeds: {len(problematic_feeds)}")
        
        if problematic_feeds:
            print("\nProblematic feeds to investigate:")
            for url, issue in problematic_feeds[:5]:  # Show first 5
                print(f"  - {url}")
                print(f"    Issue: {issue}")

# ==================== MAIN EXECUTION ====================

def main():
    print("🚀 Starting SustainNews Aggregator (Enhanced Version)")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    aggregator = NewsAggregator()
    
    # Optional: Run health check first
    # aggregator.run_health_check()
    # print("\n" + "=" * 50 + "\n")
    
    # Fetch from RSS feeds with tier-based filtering
    aggregator.fetch_rss_feeds()
    
    print("=" * 50)
    print(f"📥 Total articles fetched: {aggregator.stats['total_fetched']}")
    
    # Process articles
    aggregator.deduplicate_articles()
    aggregator.process_articles()
    
    # Save results
    aggregator.save_articles()
    
    print("\n" + "=" * 50)
    print("🎉 SustainNews aggregation completed successfully!")
    print("🌐 Your updated news is available at: https://sustainthread.github.io/sustain-news/")
    print("\n📝 Next steps:")
    print("   1. Check news.json for the filtered articles")
    print("   2. Review news_detailed.json for scoring details")
    print("   3. Monitor for false positives/negatives")
    print("=" * 50)

if __name__ == "__main__":
    main()
