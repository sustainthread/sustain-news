import requests
import json
import os
from datetime import datetime, timedelta
import hashlib

# Configuration
CONFIG = {
    'newsapi_key': os.getenv('NEWS_API_KEY'),
    'mediastack_key': os.getenv('MEDIASTACK_API_KEY'),
    'keywords': [
        "sustainability", "climate", "carbon", "greenhouse", "emissions", "renewable",
        "wastewater", "pollution", "circular", "biodiversity", "chemical management",
        "supply chain", "ESG", "textile", "fashion", "clean production", "ZDHC",
        "net zero", "carbon neutral", "sustainable fashion", "ethical fashion",
        "organic cotton", "recycled polyester", "fast fashion", "slow fashion"
    ],
    'domains': [
        "bbc.com", "reuters.com", "theguardian.com", "forbes.com",
        "businessoffashion.com", "ecotextile.com", "sourcingjournal.com",
        "fashionunited.com", "bloomberg.com", "greenbiz.com", "voguebusiness.com"
    ]
}

class NewsAggregator:
    def __init__(self):
        self.articles = []
        
    def fetch_newsapi(self):
        """Fetch news from NewsAPI"""
        print("📡 Fetching from NewsAPI...")
        
        for keyword in CONFIG['keywords']:
            try:
                url = "https://newsapi.org/v2/everything"
                params = {
                    'q': keyword,
                    'domains': ','.join(CONFIG['domains']),
                    'from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                    'sortBy': 'relevancy',
                    'pageSize': 50,
                    'apiKey': CONFIG['newsapi_key']
                }
                
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for article in data.get('articles', []):
                        article['source'] = 'newsapi'
                        article['keyword'] = keyword
                        self.articles.append(article)
                    print(f"✅ Found {len(data.get('articles', []))} articles for '{keyword}'")
                else:
                    print(f"❌ NewsAPI error for '{keyword}': {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error fetching from NewsAPI for '{keyword}': {e}")
    
    def fetch_mediastack(self):
        """Fetch news from MediaStack"""
        print("📡 Fetching from MediaStack...")
        
        for keyword in CONFIG['keywords']:
            try:
                url = "http://api.mediastack.com/v1/news"
                params = {
                    'access_key': CONFIG['mediastack_key'],
                    'keywords': keyword,
                    'languages': 'en',
                    'limit': 50,
                    'sort': 'published_desc'
                }
                
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for article in data.get('data', []):
                        # Convert MediaStack format to match NewsAPI
                        formatted_article = {
                            'title': article.get('title'),
                            'description': article.get('description'),
                            'url': article.get('url'),
                            'publishedAt': article.get('published_at'),
                            'source': article.get('source'),  # This is a string from MediaStack
                            'content': article.get('description'),
                            'keyword': keyword,
                            'source_api': 'mediastack'
                        }
                        self.articles.append(formatted_article)
                    print(f"✅ Found {len(data.get('data', []))} articles for '{keyword}'")
                else:
                    print(f"❌ MediaStack error for '{keyword}': {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error fetching from MediaStack for '{keyword}': {e}")
    
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
    
    def calculate_relevance_score(self, article):
        """Calculate relevance score based on keywords"""
        content = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
        score = 0
        
        for keyword in CONFIG['keywords']:
            if keyword.lower() in content:
                score += 1
        
        return score
    
    def get_source_name(self, article):
        """Safely get source name whether it's a string or object"""
        source = article.get('source')
        if isinstance(source, dict):
            return source.get('name', 'Unknown Source')
        elif isinstance(source, str):
            return source
        else:
            return 'Unknown Source'
    
    def process_articles(self):
        """Process and clean articles"""
        print("🔧 Processing articles...")
        
        processed_articles = []
        for article in self.articles:
            # Ensure all required fields exist
            processed_article = {
                'title': article.get('title', 'No Title'),
                'description': article.get('description', ''),
                'url': article.get('url', ''),
                'publishedAt': article.get('publishedAt', ''),
                'source': self.get_source_name(article),  # Use the safe method
                'content': article.get('content', ''),
                'keyword': article.get('keyword', ''),
                'relevance_score': self.calculate_relevance_score(article),
                'api_source': article.get('source_api', 'newsapi')
            }
            processed_articles.append(processed_article)
        
        # Sort by relevance score and date
        processed_articles.sort(key=lambda x: (x['relevance_score'], x['publishedAt']), reverse=True)
        self.articles = processed_articles
    
    def save_articles(self):
        """Save articles to JSON files"""
        print("💾 Saving articles...")
        
        # Save raw data
        with open('news_raw.json', 'w', encoding='utf-8') as f:
            json.dump({
                'last_updated': datetime.now().isoformat(),
                'total_articles': len(self.articles),
                'articles': self.articles
            }, f, indent=2, ensure_ascii=False)
        
        # Save clean data for frontend
        with open('news.json', 'w', encoding='utf-8') as f:
            json.dump({
                'last_updated': datetime.now().isoformat(),
                'total_articles': len(self.articles),
                'articles': self.articles[:100]  # Limit for frontend
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(self.articles)} articles to news.json")

def main():
    aggregator = NewsAggregator()
    
    # Fetch from both APIs
    aggregator.fetch_newsapi()
    aggregator.fetch_mediastack()
    
    print(f"📊 Total articles fetched: {len(aggregator.articles)}")
    
    # Process articles
    aggregator.deduplicate_articles()
    aggregator.process_articles()
    
    # Save results
    aggregator.save_articles()
    
    print("🎉 News aggregation completed successfully!")

if __name__ == "__main__":
    main()
