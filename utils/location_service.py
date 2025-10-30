"""
Real-time location detection and nearby resources finder
Uses browser geolocation API + OpenStreetMap data
"""

import requests
from typing import Dict, List, Optional

def get_user_location_from_ip() -> Optional[Dict]:
    """
    Get approximate location from IP address (fallback method)
    Returns: {'city': 'Mumbai', 'state': 'Maharashtra', 'lat': 19.0760, 'lon': 72.8777}
    """
    try:
        response = requests.get('http://ip-api.com/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data.get('city'),
                'state': data.get('regionName'),
                'country': data.get('country'),
                'lat': data.get('lat'),
                'lon': data.get('lon'),
                'zip': data.get('zip')
            }
    except Exception as e:
        print(f"IP location error: {e}")
    return None

def get_location_details(city_name: str) -> Optional[Dict]:
    """
    Get detailed location info using Nominatim (OpenStreetMap)
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f'{city_name}, India',
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {'User-Agent': 'StartupSathi/1.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            results = response.json()
            if results:
                loc = results[0]
                address = loc.get('address', {})
                return {
                    'city': address.get('city') or address.get('town') or address.get('village'),
                    'state': address.get('state'),
                    'district': address.get('state_district'),
                    'country': address.get('country'),
                    'lat': float(loc.get('lat')),
                    'lon': float(loc.get('lon')),
                    'display_name': loc.get('display_name')
                }
    except Exception as e:
        print(f"Location details error: {e}")
    return None

def find_nearby_businesses(lat: float, lon: float, business_type: str, radius_km: int = 10) -> List[Dict]:
    """
    Find nearby businesses using Overpass API (OpenStreetMap)
    business_type: 'shop', 'market', 'bank', 'government', 'training_center', etc.
    """
    try:
        # Map business types to OpenStreetMap tags
        tag_mapping = {
            'shop': 'shop',
            'market': 'marketplace',
            'bank': 'bank',
            'government': 'government',
            'training': 'training',
            'supplier': 'wholesale',
            'raw_materials': 'trade'
        }
        
        osm_tag = tag_mapping.get(business_type, business_type)
        radius_meters = radius_km * 1000
        
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="{osm_tag}"](around:{radius_meters},{lat},{lon});
          way["amenity"="{osm_tag}"](around:{radius_meters},{lat},{lon});
          node["shop"](around:{radius_meters},{lat},{lon});
          way["shop"](around:{radius_meters},{lat},{lon});
        );
        out center 20;
        """
        
        response = requests.post(overpass_url, data=query, timeout=30)
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for element in data.get('elements', [])[:20]:
                tags = element.get('tags', {})
                center = element.get('center', element)
                
                results.append({
                    'name': tags.get('name', f'{business_type.title()} in your area'),
                    'type': business_type,
                    'address': tags.get('addr:full') or tags.get('addr:street', 'Address not available'),
                    'phone': tags.get('phone', ''),
                    'website': tags.get('website', ''),
                    'lat': center.get('lat'),
                    'lon': center.get('lon'),
                    'distance_km': calculate_distance(lat, lon, center.get('lat', lat), center.get('lon', lon))
                })
            
            return sorted(results, key=lambda x: x['distance_km'])[:10]
    except Exception as e:
        print(f"Nearby businesses error: {e}")
    return []

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def get_local_market_insights(city: str, business_category: str) -> Dict:
    """
    Get market insights specific to location and business type
    """
    try:
        # Search for market trends
        from utils.web_search import search_duckduckgo
        
        query = f"{city} {business_category} business market demand trends 2024 2025"
        results = search_duckduckgo(query, num_results=5)
        
        insights = {
            'demand_level': 'Medium to High',
            'competition': 'Moderate',
            'growth_potential': 'Good',
            'trends': []
        }
        
        if results:
            for result in results[:3]:
                insights['trends'].append({
                    'title': result['title'],
                    'info': result['snippet']
                })
        
        return insights
    except Exception as e:
        print(f"Market insights error: {e}")
        return {'demand_level': 'Unknown', 'trends': []}

def get_weather_and_season(lat: float, lon: float) -> Dict:
    """
    Get current weather and season info (useful for agri/seasonal businesses)
    """
    try:
        # Using free weather API
        url = f"https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': lat,
            'longitude': lon,
            'current_weather': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            current = data.get('current_weather', {})
            
            temp = current.get('temperature', 0)
            # Determine season based on temperature
            if temp > 30:
                season = 'Summer'
            elif temp > 20:
                season = 'Spring/Autumn'
            else:
                season = 'Winter'
            
            return {
                'temperature': temp,
                'season': season,
                'weather_code': current.get('weathercode', 0)
            }
    except Exception as e:
        print(f"Weather error: {e}")
    return {'season': 'Current Season'}
