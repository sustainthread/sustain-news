import feedparser
import json
import os
from datetime import datetime, timedelta
import hashlib
import re
from urllib.parse import urlparse

# Configuration - RSS Feeds for sustainability/fashion topics
RSS_FEEDS = [
    # Environment/Climate feeds
    'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
    'https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml',
    'https://www.theguardian.com/us/environment/rss',
    'https://feeds.npr.org/1005/rss.xml',  # NPR Environment
    'https://www.sciencedaily.com/rss/earth_climate/environment.xml',
    
    # Fashion/Sustainability specific
    'https://www.businessoffashion.com/rss',
    'https://www.ecotextile.com/rss',
    'https://sourcingjournal.com/feed/',
    'https://fashionunited.com/feed/',
    'https://www.voguebusiness.com/feed/rss',
    
    # General sustainability
    'https://www.greenbiz.com/rss',
    'https://feeds.feedburner.com/SustainableBrands',
    'https://www.triplepundit.com/feed/',
    
    # NEW INTERNATIONAL SOURCES - Use more specific RSS feeds
    'https://www.aljazeera.com/xml/rss/all.xml',
    'https://rss.dw.com/rdf/rss-en-all',
    'https://www.france24.com/en/rss',
    # Use specific feeds for The Hindu instead of general news
    'https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss',
    'https://www.thehindu.com/business/feeder/default.rss',
    'https://www.euronews.com/rss?format=mrss&level=theme&name=green',
    'https://feeds.reuters.com/reuters/environment',
    'https://feeds.reuters.com/reuters/scienceNews',
]

# Enhanced keywords for better relevance scoring
KEYWORDS = [
    # Core sustainability
    "sustainability", "sustainable", "esg", "circular economy", "climate", "carbon",
    "emissions", "renewable", "greenhouse", "biodiversity", "conservation",
    "pollution", "waste", "recycling", "upcycling", "eco-friendly", "green",
    "environment", "ecological", "clean energy", "solar", "wind power",
    
    # Fashion specific
    "fashion", "textile", "apparel", "clothing", "garment", "cotton", "polyester",
    "supply chain", "ethical", "organic", "recycled", "sustainable fashion",
    "circular fashion", "ethical fashion", "fast fashion", "slow fashion",
    "fashion industry", "textile industry", "apparel industry",
    
    # Business & ESG
    "esg", "environmental", "social", "governance", "corporate responsibility",
    "sustainable business", "green business", "clean production", "ethical sourcing",
    "sustainable development", "green technology", "cleantech",
    
    # Technical terms
    "chemical management", "zdhc", "water conservation", "energy efficiency",
    "carbon footprint", "net zero", "carbon neutral", "decarbonization",
    "waste management", "plastic pollution", "air quality"
]

# STRONG negative keywords - filter out clearly irrelevant content
STRONG_NEGATIVE_KEYWORDS = [
    # Politics
    "election", "trump", "biden", "president", "senate", "congress", "vote", "voting",
    "political", "politician", "government", "policy", "law", "legal", "court", "judge",
    "election results", "campaign", "democrat", "republican",
    
    # Sports
    "football", "basketball", "soccer", "nfl", "nba", "baseball", "tennis", "olympics",
    "cricket", "sports", "player", "team", "match", "game", "championship",
    
    # Entertainment
    "celebrity", "movie", "hollywood", "oscars", "grammy", "netflix", "disney",
    "entertainment", "actor", "actress", "film", "music", "song", "album",
    
    # Crime & Negative news
    "crime", "murder", "rape", "sexual", "harassment", "assault", "violence",
    "police", "investigation", "case", "lawsuit", "arrest", "charged",
    
    # Regional/State politics (common in The Hindu)
    "andhra pradesh", "tamil nadu", "karnataka", "kerala", "delhi", "mumbai",
    "chief minister", "state government", "assembly", "elections",
    
    # Completely unrelated
    "crypto", "bitcoin", "stock market", "real estate", "recipe", "cooking",
    "weather", "forecast", "horoscope", "astrology"
]

# Sources that need stricter filtering
GENERAL_NEWS_SOURCES = [
    'thehindu.com', 'aljazeera.com', 'reuters.com', 'dw.com', 'france24.com'
]

# Trusted sustainability sources - these get bonus points
SUSTAINABILITY_SOURCES = [
    'greenbiz.com', 'sustainablebrands.com', 'ecotextile.com', 
    'businessoffashion.com', 'sourcingjournal.com', 'voguebusiness.com',
    'triplepundit.com', 'sciencedaily.com'
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
}

class NewsAggregator:
    def __init__(self):
        self.articles = []
        
    def is_source_allowed(self, feed_url):
        """Check if we should fetch from this source based on robots.txt and terms"""
        friendly_sources = [
            'aljazeera.com', 'dw.com', 'france24.com', 'thehindu.com', 
            'euronews.com', 'reuters.com', 'bbci.co.uk', 'nytimes.com', 
            'theguardian.com', 'npr.org', 'sciencedaily.com', 'businessoffashion.com',
            'ecotextile.com', 'sourcingjournal.com', 'fashionunited.com', 
            'voguebusiness.com', 'greenbiz.com', 'feedburner.com', 'triplepundit.com'
        ]
        
        domain = self.get_domain_name(feed_url)
        return any(friendly in domain for friendly in friendly_sources)

    def fetch_rss_feeds(self):
        """Fetch news from RSS feeds"""
        print("📡 Fetching from RSS feeds...")
        
        for feed_url in RSS_FEEDS:
            try:
                if not self.is_source_allowed(feed_url):
                    print(f"⏭️  Skipping unverified source: {feed_url}")
                    continue
                    
                print(f"Fetching from: {self.get_domain_name(feed_url)}")
                feed = feedparser.parse(feed_url)
                
                articles_from_feed = 0
                for entry in feed.entries[:15]:
                    published_time = self.get_published_time(entry)
                    if published_time and published_time < (datetime.now() - timedelta(days=7)):
                        continue
                    
                    # Calculate relevance score with source-specific filtering
                    relevance_score = self.calculate_relevance_score(entry, feed_url)
                    
                    # Apply stricter filtering for general news sources
                    domain = self.get_domain_name(feed_url)
                    if any(source in domain for source in GENERAL_NEWS_SOURCES):
                        # General news sources need higher relevance scores
                        if relevance_score >= 3:
                            article = self.create_article(entry, feed_url, relevance_score)
                            self.articles.append(article)
                            articles_from_feed += 1
                    else:
                        # Sustainability-focused sources can have lower thresholds
                        if relevance_score >= 1:
                            article = self.create_article(entry, feed_url, relevance_score)
                            self.articles.append(article)
                            articles_from_feed += 1
                    
                print(f"✅ Found {articles_from_feed} relevant articles from {self.get_domain_name(feed_url)}")
                
            except Exception as e:
                print(f"❌ Error fetching from {feed_url}: {e}")
                continue
    
    def create_article(self, entry, feed_url, relevance_score):
        """Create article dictionary"""
        published_time = self.get_published_time(entry)
        return {
            'title': entry.title,
            'description': self.get_clean_description(entry),
            'url': entry.link,
            'publishedAt': published_time.isoformat() if published_time else datetime.now().isoformat(),
            'source': self.get_proper_source_name(feed_url, entry),
            'content': self.get_clean_description(entry),
            'relevance_score': relevance_score,
            'api_source': 'rss',
        }
    
    def get_published_time(self, entry):
        """Extract publication time from RSS entry"""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
        return None
    
    def get_proper_source_name(self, feed_url, entry):
        """Get proper source name from domain mapping"""
        domain = self.get_domain_name(feed_url)
        
        for key, name in SOURCE_NAME_MAP.items():
            if key in domain:
                return name
        
        clean_name = domain.replace('www.', '').split('.')[0]
        return clean_name.title()
    
    def get_domain_name(self, url):
        """Extract domain name from URL"""
        return urlparse(url).netloc
    
    def get_clean_description(self, entry):
        """Extract and clean description - keep it very short for legal safety"""
        description = ""
        
        if hasattr(entry, 'description'):
            description = entry.description
        elif hasattr(entry, 'summary'):
            description = entry.summary
        
        # Remove HTML tags and limit length for legal safety
        clean_desc = re.sub('<[^<]+?>', '', description)
        
        # Conservative approach - limit to 100 chars
        if '.' in clean_desc[:100]:
            sentences = clean_desc.split('.')
            if len(sentences[0]) < 100:
                clean_desc = sentences[0] + '.' if len(sentences) > 1 else sentences[0]
            else:
                clean_desc = clean_desc[:97] + '...'
        else:
            clean_desc = clean_desc[:97] + '...'
        
        return clean_desc.strip()
    
    def calculate_relevance_score(self, entry, feed_url):
        """Calculate balanced relevance score with strong negative filtering"""
        content = f"{entry.title} {self.get_clean_description(entry)}".lower()
        score = 0
        
        # Base keyword matching
        for keyword in KEYWORDS:
            if keyword.lower() in content:
                score += 2  # Increased weight for positive matches
        
        # STRONG negative filtering - auto-reject clearly irrelevant content
        for keyword in STRONG_NEGATIVE_KEYWORDS:
            if keyword.lower() in content:
                score -= 10  # Very strong penalty - will almost certainly exclude
        
        # Bonus for trusted sustainability sources
        domain = self.get_domain_name(feed_url)
        if any(source in domain for source in SUSTAINABILITY_SOURCES):
            score += 3  # Higher bonus for known sustainability-focused sources
        
        # Bonus for multiple keyword matches
        keyword_matches = sum(1 for keyword in KEYWORDS if keyword.lower() in content)
        if keyword_matches >= 3:
            score += 3
        elif keyword_matches >= 2:
            score += 2
        
        # Recency bonus (only if article is already relevant)
        if score > 0:
            published_time = self.get_published_time(entry)
            if published_time:
                days_old = (datetime.now() - published_time).days
                if days_old <= 1:
                    score += 2
                elif days_old <= 3:
                    score += 1
        
        return max(0, score)
    
    def deduplicate_articles(self):
        """Remove duplicate articles based on URL and title"""
        print("🔄 Deduplicating articles...")
        
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in self.articles:
            url = article.get('url', '').split('?')[0]
            title = article.get('title', '').lower().strip()
            
            url_hash = hashlib.md5(url.encode()).hexdigest()
            title_hash = hashlib.md5(title.encode()).hexdigest()
            
            if url_hash not in seen_urls and title_hash not in seen_titles:
                seen_urls.add(url_hash)
                seen_titles.add(title_hash)
                unique_articles.append(article)
        
        print(f"✅ Removed {len(self.articles) - len(unique_articles)} duplicates")
        self.articles = unique_articles
    
    def process_articles(self):
        """Process and clean articles"""
        print("🔧 Processing articles...")
        
        # Sort by relevance score and date
        self.articles.sort(key=lambda x: (x['relevance_score'], x['publishedAt']), reverse=True)
        
        print(f"📊 Total unique articles: {len(self.articles)}")
        
        # Show score distribution
        score_counts = {}
        for article in self.articles:
            score = article['relevance_score']
            score_counts[score] = score_counts.get(score, 0) + 1
        
        print("📈 Score distribution:")
        for score, count in sorted(score_counts.items(), reverse=True):
            print(f"   - Score {score}: {count} articles")
        
        # Show top articles by relevance
        top_articles = [a for a in self.articles if a['relevance_score'] >= 5][:5]
        if top_articles:
            print("🏆 Top relevant articles:")
            for article in top_articles:
                print(f"   - {article['title']} (Score: {article['relevance_score']}) - {article['source']}")
    
    def save_articles(self):
        """Save articles to JSON files - compatible with current frontend"""
        print("💾 Saving articles...")
        
        # Use source-specific thresholds
        relevant_articles = []
        for article in self.articles:
            source_domain = article['source'].lower()
            if any(source in source_domain for source in GENERAL_NEWS_SOURCES):
                # General news needs higher scores
                if article['relevance_score'] >= 3:
                    relevant_articles.append(article)
            else:
                # Sustainability sources can have lower scores
                if article['relevance_score'] >= 1:
                    relevant_articles.append(article)
        
        # Format compatible with your current frontend
        frontend_data = {
            'status': 'ok',
            'totalResults': len(relevant_articles),
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
                for article in relevant_articles[:100]
            ]
        }
        
        # Save to news.json
        with open('news.json', 'w', encoding='utf-8') as f:
            json.dump(frontend_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(relevant_articles)} relevant articles to news.json")

def main():
    print("🚀 Starting SustainNews Aggregation...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    aggregator = NewsAggregator()
    
    # Fetch from RSS feeds
    aggregator.fetch_rss_feeds()
    
    print(f"📊 Total articles fetched: {len(aggregator.articles)}")
    
    # Process articles
    aggregator.deduplicate_articles()
    aggregator.process_articles()
    
    # Save results
    aggregator.save_articles()
    
    print("🎉 SustainNews aggregation completed successfully!")
    print("🌐 Your updated news will be available at: https://sustainthread.github.io/sustain-news/")

if __name__ == "__main__":
    main()
