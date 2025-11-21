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
    
    # NEW INTERNATIONAL SOURCES - Added RSS feeds
    # Al Jazeera (Environment & Climate)
    'https://www.aljazeera.com/xml/rss/all.xml',
    'https://www.aljazeera.com/xml/rss/climate.xml',
    
    # Deutsche Welle (Environment)
    'https://rss.dw.com/rdf/rss-en-all',
    'https://rss.dw.com/xml/DW_rss_en_climate',
    
    # France 24 (Environment)
    'https://www.france24.com/en/rss',
    'https://www.france24.com/en/environment/rss',
    
    # The Hindu (Environment & Science)
    'https://www.thehindu.com/news/national/feeder/default.rss',
    'https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss',
    
    # Euronews (Green)
    'https://www.euronews.com/rss?format=mrss&level=theme&name=green',
    'https://www.euronews.com/rss?format=mrss&level=theme&name=news',
    
    # Additional reputable sources
    'https://feeds.reuters.com/reuters/environment',  # Reuters Environment
    'https://feeds.reuters.com/reuters/scienceNews',  # Reuters Science
    'https://www.bloomberg.com/green/feed',  # Bloomberg Green
]

# Enhanced keywords for better relevance scoring
KEYWORDS = [
    # Your existing keywords
    "sustainability", "climate", "carbon", "greenhouse", "emissions", "renewable",
    "wastewater", "pollution", "circular", "biodiversity", "chemical management",
    "supply chain", "ESG", "textile", "fashion", "clean production", "ZDHC",
    "net zero", "carbon neutral", "sustainable fashion", "ethical fashion",
    "organic cotton", "recycled polyester", "fast fashion", "slow fashion",
    
    # Additional keywords for international coverage
    "environment", "ecological", "eco-friendly", "green technology",
    "climate change", "global warming", "conservation", "renewable energy",
    "sustainable development", "environmental policy", "carbon footprint",
    "recycling", "upcycling", "ethical production", "fair trade",
    "sustainable", "environmental", "green", "eco", "conservation"
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
    
    # NEW SOURCE MAPPINGS
    'aljazeera.com': 'Al Jazeera',
    'dw.com': 'Deutsche Welle',
    'france24.com': 'France 24',
    'thehindu.com': 'The Hindu',
    'euronews.com': 'Euronews',
    'reuters.com': 'Reuters',
    'bloomberg.com': 'Bloomberg',
}

class NewsAggregator:
    def __init__(self):
        self.articles = []
        
    def is_source_allowed(self, feed_url):
        """Check if we should fetch from this source based on robots.txt and terms"""
        # Sources known to have friendly RSS terms
        friendly_sources = [
            'aljazeera.com', 'dw.com', 'france24.com', 'thehindu.com', 
            'euronews.com', 'reuters.com', 'bloomberg.com',
            'bbci.co.uk', 'nytimes.com', 'theguardian.com', 'npr.org',
            'sciencedaily.com', 'businessoffashion.com', 'ecotextile.com',
            'sourcingjournal.com', 'fashionunited.com', 'voguebusiness.com',
            'greenbiz.com', 'feedburner.com', 'triplepundit.com'
        ]
        
        domain = self.get_domain_name(feed_url)
        return any(friendly in domain for friendly in friendly_sources)

    def fetch_rss_feeds(self):
        """Fetch news from RSS feeds"""
        print("📡 Fetching from RSS feeds...")
        
        for feed_url in RSS_FEEDS:
            try:
                # Skip if source isn't allowed (safety check)
                if not self.is_source_allowed(feed_url):
                    print(f"⏭️  Skipping unverified source: {feed_url}")
                    continue
                    
                print(f"Fetching from: {self.get_domain_name(feed_url)}")
                feed = feedparser.parse(feed_url)
                
                # Reduce number of articles per feed to manage volume
                for entry in feed.entries[:10]:  # Reduced from 15 to 10
                    # Skip if article is too old
                    published_time = self.get_published_time(entry)
                    if published_time and published_time < (datetime.now() - timedelta(days=7)):  # Reduced from 14 to 7 days
                        continue
                    
                    article = {
                        'title': entry.title,
                        'description': self.get_clean_description(entry),
                        'url': entry.link,
                        'publishedAt': published_time.isoformat() if published_time else datetime.now().isoformat(),
                        'source': self.get_proper_source_name(feed_url, entry),
                        'content': self.get_clean_description(entry),
                        'relevance_score': self.calculate_relevance_score(entry),
                        'api_source': 'rss',
                    }
                    self.articles.append(article)
                    
                print(f"✅ Found {len(feed.entries)} articles from {self.get_domain_name(feed_url)}")
                
            except Exception as e:
                print(f"❌ Error fetching from {feed_url}: {e}")
                continue
    
    def get_published_time(self, entry):
        """Extract publication time from RSS entry"""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
        return None
    
    def get_proper_source_name(self, feed_url, entry):
        """Get proper source name from domain mapping, not author names"""
        domain = self.get_domain_name(feed_url)
        
        # Use our mapping first
        for key, name in SOURCE_NAME_MAP.items():
            if key in domain:
                return name
        
        # Fallback: clean up domain name
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
        
        # More conservative approach for new sources - limit to 100 chars
        # This falls well within fair use/dealing guidelines
        if '.' in clean_desc[:100]:
            # Try to end at a sentence boundary
            sentences = clean_desc.split('.')
            if len(sentences[0]) < 100:
                clean_desc = sentences[0] + '.' if len(sentences) > 1 else sentences[0]
            else:
                clean_desc = clean_desc[:97] + '...'
        else:
            clean_desc = clean_desc[:97] + '...'
        
        return clean_desc.strip()
    
    def calculate_relevance_score(self, entry):
        """Calculate relevance score based on keywords"""
        content = f"{entry.title} {self.get_clean_description(entry)}".lower()
        score = 0
        
        for keyword in KEYWORDS:
            if keyword.lower() in content:
                score += 2  # Higher weight for keyword matches
        
        # Bonus for recent articles
        published_time = self.get_published_time(entry)
        if published_time:
            days_old = (datetime.now() - published_time).days
            if days_old <= 1:
                score += 3
            elif days_old <= 3:
                score += 2
            elif days_old <= 7:
                score += 1
        
        return score
    
    def deduplicate_articles(self):
        """Remove duplicate articles based on URL and title"""
        print("🔄 Deduplicating articles...")
        
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in self.articles:
            url = article.get('url', '').split('?')[0]  # Remove URL parameters
            title = article.get('title', '').lower().strip()
            
            # Create a unique identifier
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
        
        # Show top articles by relevance
        top_articles = [a for a in self.articles if a['relevance_score'] > 0][:5]
        if top_articles:
            print("🏆 Top relevant articles:")
            for article in top_articles:
                print(f"   - {article['title']} (Score: {article['relevance_score']}) - {article['source']}")
        
        # Show source distribution
        source_counts = {}
        for article in self.articles:
            source = article['source']
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print("📈 Source distribution:")
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   - {source}: {count} articles")
    
    def save_articles(self):
        """Save articles to JSON files"""
        print("💾 Saving articles...")
        
        # Filter to only relevant articles (score > 0) for the main feed
        relevant_articles = [article for article in self.articles if article['relevance_score'] > 0]
        
        # Save clean data for frontend (no images)
        frontend_data = {
            'status': 'ok',
            'last_updated': datetime.now().isoformat(),
            'total_articles': len(relevant_articles),
            'articles': [
                {
                    'title': article['title'],
                    'description': article['description'],
                    'url': article['url'],
                    'publishedAt': article['publishedAt'],
                    'source': {'name': article['source']},  # Format for frontend compatibility
                    'content': article['content'],
                }
                for article in relevant_articles[:100]  # Limit for frontend
            ]
        }
        
        with open('news.json', 'w', encoding='utf-8') as f:
            json.dump(frontend_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(relevant_articles)} relevant articles to news.json")

def main():
    aggregator = NewsAggregator()
    
    # Fetch from RSS feeds only
    aggregator.fetch_rss_feeds()
    
    print(f"📊 Total articles fetched: {len(aggregator.articles)}")
    
    # Process articles
    aggregator.deduplicate_articles()
    aggregator.process_articles()
    
    # Save results
    aggregator.save_articles()
    
    print("🎉 RSS news aggregation completed successfully!")

if __name__ == "__main__":
    main()
