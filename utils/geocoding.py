import requests

def geocode_place(place_name):
    """Get lat/lng for a place using Nominatim"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': place_name,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'in'  # Restrict to India
        }
        headers = {'User-Agent': 'StartupSathi/1.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data:
            return {
                'lat': float(data[0]['lat']),
                'lng': float(data[0]['lon']),
                'display_name': data[0]['display_name']
            }
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

def query_overpass(lat, lng, radius=5000):
    """
    Find nearby resources using Overpass API
    radius: in meters (default 5km)
    """
    try:
        query = f"""
        [out:json][timeout:25];
        (
          node["shop"="hardware"](around:{radius},{lat},{lng});
          node["shop"="farm"](around:{radius},{lat},{lng});
          node["shop"="general"](around:{radius},{lat},{lng});
          node["amenity"="marketplace"](around:{radius},{lat},{lng});
          node["office"="government"](around:{radius},{lat},{lng});
          node["amenity"="training"](around:{radius},{lat},{lng});
          node["amenity"="bank"](around:{radius},{lat},{lng});
          node["office"="ngo"](around:{radius},{lat},{lng});
        );
        out center;
        """
        
        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=30)
        data = response.json()
        
        resources = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            resources.append({
                'name': tags.get('name', 'Unnamed'),
                'type': tags.get('shop') or tags.get('amenity') or tags.get('office', 'unknown'),
                'lat': element.get('lat'),
                'lng': element.get('lon'),
                'address': tags.get('addr:full', '') or tags.get('addr:street', ''),
                'phone': tags.get('phone', ''),
                'details': tags
            })
        
        return resources
    except Exception as e:
        print(f"Overpass query error: {e}")
        return []

def find_nearby_resources(location, resource_types=None):
    """
    Find resources near a location
    location: place name or dict with lat/lng
    resource_types: list of types to filter (optional)
    """
    # Get coordinates if location is a place name
    if isinstance(location, str):
        coords = geocode_place(location)
        if not coords:
            return []
        lat, lng = coords['lat'], coords['lng']
    else:
        lat = location.get('lat')
        lng = location.get('lng')
    
    if not lat or not lng:
        return []
    
    # Query Overpass
    resources = query_overpass(lat, lng)
    
    # Filter by type if specified
    if resource_types:
        resources = [r for r in resources if r['type'] in resource_types]
    
    return resources

def categorize_resources(resources):
    """Categorize resources by type"""
    categories = {
        'suppliers': [],
        'markets': [],
        'banks': [],
        'government': [],
        'training': [],
        'other': []
    }
    
    for resource in resources:
        rtype = resource['type']
        if rtype in ['hardware', 'farm', 'general']:
            categories['suppliers'].append(resource)
        elif rtype == 'marketplace':
            categories['markets'].append(resource)
        elif rtype == 'bank':
            categories['banks'].append(resource)
        elif rtype == 'government':
            categories['government'].append(resource)
        elif rtype == 'training':
            categories['training'].append(resource)
        else:
            categories['other'].append(resource)
    
    return categories
