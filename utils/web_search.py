"""
Web search and real-time data fetching utilities
Enhanced with context-aware Google-style search and filtering
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

def smart_google_search(query, user_context=None, num_results=10):
    """
    Enhanced Google-style search with user context filtering
    
    Args:
        query: Search query string
        user_context: Dict with {name, location, interests, budget}
        num_results: Number of results to return
    
    Returns:
        Filtered and personalized search results
    """
    try:
        # Build context-aware search query
        enhanced_query = query
        
        if user_context:
            location = user_context.get('location') or user_context.get('village')
            interests = user_context.get('interests')
            budget = user_context.get('budget')
            
            # Add location to query
            if location:
                enhanced_query = f"{query} in {location} India"
            
            # Add budget context for business searches
            if budget and any(word in query.lower() for word in ['business', 'startup', 'idea', 'invest']):
                if budget <= 10000:
                    enhanced_query += " low investment under 10000"
                elif budget <= 50000:
                    enhanced_query += " small investment 10000 to 50000"
                elif budget <= 100000:
                    enhanced_query += " medium investment"
            
            # Add interest context
            if interests and 'business' in query.lower():
                enhanced_query += f" {interests}"
            
            # Add year for trending searches
            enhanced_query += " 2025 latest"
        
        print(f"🔍 Smart Search Query: {enhanced_query}")
        
        # Search using multiple sources
        results = []
        
        # Try web scraping Google (respectful, limited)
        google_results = _scrape_google_search(enhanced_query, num_results=5)
        results.extend(google_results)
        
        # Also get DuckDuckGo results
        ddg_results = search_duckduckgo(enhanced_query, num_results=5)
        results.extend(ddg_results)
        
        # Filter and rank results based on user context
        filtered_results = _filter_by_context(results, user_context)
        
        return filtered_results[:num_results]
        
    except Exception as e:
        print(f"Smart search error: {e}")
        return search_duckduckgo(query, num_results)

def _scrape_google_search(query, num_results=5):
    """
    Scrape Google search results (respectful, limited use)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Find search result divs
        for g in soup.find_all('div', class_='g')[:num_results]:
            try:
                # Extract title
                title_elem = g.find('h3')
                title = title_elem.get_text() if title_elem else ''
                
                # Extract snippet
                snippet_elem = g.find('div', class_=['VwiC3b', 'yXK7lf'])
                snippet = snippet_elem.get_text() if snippet_elem else ''
                
                # Extract URL
                link_elem = g.find('a')
                url = link_elem.get('href') if link_elem else ''
                
                if title and snippet:
                    results.append({
                        'title': title,
                        'snippet': snippet,
                        'url': url,
                        'source': 'Google'
                    })
            except:
                continue
        
        return results
        
    except Exception as e:
        print(f"Google scraping error: {e}")
        return []

def _filter_by_context(results, user_context):
    """
    Filter and rank search results based on user context
    """
    if not user_context:
        return results
    
    location = (user_context.get('location') or user_context.get('village') or '').lower()
    interests = (user_context.get('interests') or '').lower()
    budget = user_context.get('budget', 0)
    
    scored_results = []
    
    for result in results:
        score = 0
        text = (result.get('title', '') + ' ' + result.get('snippet', '')).lower()
        
        # Location relevance
        if location and location in text:
            score += 10
        
        # Interest relevance
        if interests:
            interest_words = interests.split()
            for word in interest_words:
                if len(word) > 3 and word in text:
                    score += 5
        
        # Budget relevance
        if budget:
            if budget <= 10000 and any(word in text for word in ['low investment', 'cheap', 'minimal', 'small budget']):
                score += 8
            elif budget <= 50000 and any(word in text for word in ['affordable', 'medium investment', 'moderate']):
                score += 8
        
        # Recency bonus (2024-2025)
        if any(year in text for year in ['2025', '2024', 'latest', 'new', 'current']):
            score += 3
        
        # Women entrepreneur bonus
        if any(word in text for word in ['women', 'woman', 'female', 'mahila']):
            score += 5
        
        # Government scheme bonus
        if any(word in text for word in ['government', 'scheme', 'subsidy', 'loan', 'pmegp', 'mudra']):
            score += 4
        
        result['relevance_score'] = score
        scored_results.append(result)
    
    # Sort by score
    scored_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return scored_results

def search_duckduckgo(query, num_results=5):
    """
    Search using DuckDuckGo Instant Answer API (free, no API key needed)
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': 1,
            'skip_disambig': 1
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        results = []
        
        # Get abstract
        if data.get('Abstract'):
            results.append({
                'title': data.get('Heading', query),
                'snippet': data.get('Abstract'),
                'source': data.get('AbstractSource', 'DuckDuckGo')
            })
        
        # Get related topics
        for topic in data.get('RelatedTopics', [])[:num_results]:
            if isinstance(topic, dict) and 'Text' in topic:
                results.append({
                    'title': topic.get('Text', '')[:50],
                    'snippet': topic.get('Text', ''),
                    'source': 'DuckDuckGo'
                })
        
        return results
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        return []

def search_government_schemes(business_type, location, user_category="women"):
    """
    Search for relevant government schemes using multiple queries
    """
    try:
        queries = [
            f"{business_type} business government schemes India {user_category}",
            f"PMEGP loan {business_type} {location}",
            f"Mudra loan {business_type} women entrepreneurs",
            f"startup schemes {location} {business_type}"
        ]
        
        all_results = []
        for query in queries[:2]:  # Limit to 2 queries to save time
            results = search_duckduckgo(query, num_results=3)
            all_results.extend(results)
        
        return all_results
    except Exception as e:
        print(f"Scheme search error: {e}")
        return []

def get_location_data(location_name):
    """
    Get geographic data for a location using Nominatim (OpenStreetMap)
    Free API, no key required
    """
    try:
        # Nominatim API endpoint
        url = "https://nominatim.openstreetmap.org/search"
        
        params = {
            'q': f"{location_name}, India",
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'StartupSathi/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data and len(data) > 0:
            place = data[0]
            return {
                'name': place.get('display_name'),
                'latitude': float(place.get('lat', 0)),
                'longitude': float(place.get('lon', 0)),
                'address': place.get('address', {}),
                'state': place.get('address', {}).get('state', ''),
                'district': place.get('address', {}).get('state_district', ''),
                'country': place.get('address', {}).get('country', 'India')
            }
        return None
    except Exception as e:
        print(f"Location data error: {e}")
        return None

def find_nearby_places(latitude, longitude, place_type, radius_km=20):
    """
    Find nearby places using Overpass API (OpenStreetMap)
    place_type examples: 'shop', 'marketplace', 'training', 'bank', 'government'
    """
    try:
        # Overpass API endpoint
        url = "https://overpass-api.de/api/interpreter"
        
        # Convert radius to meters
        radius_m = radius_km * 1000
        
        # Overpass QL query based on place type
        type_mapping = {
            'shop': 'shop',
            'market': 'marketplace',
            'training': 'amenity=training',
            'bank': 'amenity=bank',
            'government': 'office=government',
            'supplier': 'shop=trade'
        }
        
        osm_tag = type_mapping.get(place_type, 'shop')
        
        query = f"""
        [out:json][timeout:10];
        (
          node[{osm_tag}](around:{radius_m},{latitude},{longitude});
          way[{osm_tag}](around:{radius_m},{latitude},{longitude});
        );
        out body 20;
        """
        
        response = requests.post(url, data=query, timeout=10)
        data = response.json()
        
        places = []
        for element in data.get('elements', [])[:10]:  # Limit to 10 results
            tags = element.get('tags', {})
            lat = element.get('lat', latitude)
            lon = element.get('lon', longitude)
            
            # Calculate approximate distance
            distance_km = calculate_distance(latitude, longitude, lat, lon)
            
            place_info = {
                'name': tags.get('name', 'Unnamed'),
                'type': tags.get('shop') or tags.get('amenity') or tags.get('office') or place_type,
                'address': tags.get('addr:street', '') + ' ' + tags.get('addr:city', ''),
                'distance_km': round(distance_km, 1),
                'latitude': lat,
                'longitude': lon
            }
            places.append(place_info)
        
        return places
    except Exception as e:
        print(f"Nearby places error: {e}")
        return []

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers (Haversine formula)"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance

def get_location_based_opportunities(user_context):
    """
    Get business opportunities specific to user's location and profile
    Uses smart Google search with context filtering
    
    Args:
        user_context: Dict with {name, location, interests, budget}
    
    Returns:
        Comprehensive opportunity analysis
    """
    try:
        location = user_context.get('location') or user_context.get('village', 'India')
        interests = user_context.get('interests', 'business')
        budget = user_context.get('budget', 50000)
        
        opportunities = {
            'location': location,
            'trends': [],
            'local_demands': [],
            'competition': [],
            'government_schemes': [],
            'success_stories': []
        }
        
        # 1. Search for trending businesses in location
        trend_query = f"trending small business {location} 2025 women entrepreneurs"
        trends = smart_google_search(trend_query, user_context, num_results=5)
        opportunities['trends'] = trends
        
        # 2. Search for local market demands
        demand_query = f"high demand products services {location} market analysis"
        demands = smart_google_search(demand_query, user_context, num_results=5)
        opportunities['local_demands'] = demands
        
        # 3. Search for competition analysis
        comp_query = f"business competition {interests} {location}"
        competition = smart_google_search(comp_query, user_context, num_results=3)
        opportunities['competition'] = competition
        
        # 4. Search for government schemes
        scheme_query = f"government schemes women entrepreneurs {location} 2025"
        schemes = smart_google_search(scheme_query, user_context, num_results=5)
        opportunities['government_schemes'] = schemes
        
        # 5. Search for success stories
        success_query = f"successful women business {interests} {location} case study"
        success = smart_google_search(success_query, user_context, num_results=3)
        opportunities['success_stories'] = success
        
        return opportunities
        
    except Exception as e:
        print(f"Location opportunities error: {e}")
        return {
            'location': user_context.get('location', 'Unknown'),
            'trends': [],
            'local_demands': [],
            'competition': [],
            'government_schemes': [],
            'success_stories': [],
            'error': str(e)
        }

def get_market_trends(business_type, location="India"):
    """
    Get current market trends for a business type
    Enhanced with smart search
    """
    try:
        user_context = {'location': location}
        query = f"{business_type} business trends market analysis 2025"
        results = smart_google_search(query, user_context, num_results=8)
        
        trends = []
        for result in results:
            trends.append({
                'title': result.get('title', ''),
                'description': result.get('snippet', ''),
                'url': result.get('url', ''),
                'source': result.get('source', 'Web'),
                'relevance': 'high' if business_type.lower() in result.get('snippet', '').lower() else 'medium',
                'relevance_score': result.get('relevance_score', 0)
            })
        
        return trends
    except Exception as e:
        print(f"Market trends error: {e}")
        return []

def get_current_prices(item_name, location="India"):
    """
    Try to get current market prices for items
    """
    try:
        query = f"{item_name} price {location} today"
        results = search_duckduckgo(query, num_results=3)
        
        return results
    except Exception as e:
        print(f"Price search error: {e}")
        return []

def get_government_scheme_details(scheme_name):
    """
    Get detailed information about a specific government scheme
    """
    try:
        query = f"{scheme_name} eligibility application process India"
        results = search_duckduckgo(query, num_results=5)
        
        return results
    except Exception as e:
        print(f"Scheme details error: {e}")
        return []

def search_local_resources(business_type, location):
    """
    Comprehensive search for local business resources
    Returns: suppliers, markets, training centers, government offices
    """
    try:
        # Get location coordinates
        location_data = get_location_data(location)
        
        if not location_data:
            return {
                'location': location,
                'suppliers': [],
                'markets': [],
                'training_centers': [],
                'government_offices': [],
                'message': 'Could not find location data. Using general information.'
            }
        
        lat = location_data['latitude']
        lon = location_data['longitude']
        
        # Find nearby places
        suppliers = find_nearby_places(lat, lon, 'shop', radius_km=15)
        markets = find_nearby_places(lat, lon, 'market', radius_km=20)
        training = find_nearby_places(lat, lon, 'training', radius_km=25)
        govt_offices = find_nearby_places(lat, lon, 'government', radius_km=30)
        
        return {
            'location': location_data['name'],
            'state': location_data['state'],
            'district': location_data['district'],
            'coordinates': {
                'latitude': lat,
                'longitude': lon
            },
            'suppliers': suppliers,
            'markets': markets,
            'training_centers': training,
            'government_offices': govt_offices,
            'search_radius_km': 30
        }
    except Exception as e:
        print(f"Local resources search error: {e}")
        return {
            'error': str(e),
            'location': location,
            'suppliers': [],
            'markets': [],
            'training_centers': [],
            'government_offices': []
        }
