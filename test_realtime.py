"""
Test script for real-time data fetching capabilities
"""
import sys
sys.path.append('.')

from utils.web_search import (
    search_duckduckgo,
    get_location_data,
    search_local_resources,
    get_market_trends
)

print("🧪 Testing Real-Time Data Features\n")
print("=" * 60)

# Test 1: Web Search
print("\n1️⃣ Testing Web Search (DuckDuckGo)...")
try:
    results = search_duckduckgo("PMEGP scheme women entrepreneurs India", num_results=3)
    if results:
        print("✅ Web search working!")
        for i, result in enumerate(results[:2], 1):
            print(f"   {i}. {result['title'][:50]}...")
            print(f"      {result['snippet'][:100]}...")
    else:
        print("⚠️ No results found")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Location Data
print("\n2️⃣ Testing Location Services (OpenStreetMap)...")
try:
    location_data = get_location_data("Jaipur, Rajasthan")
    if location_data:
        print("✅ Location service working!")
        print(f"   Location: {location_data['name']}")
        print(f"   State: {location_data.get('state', 'N/A')}")
        print(f"   Coordinates: {location_data['latitude']}, {location_data['longitude']}")
    else:
        print("⚠️ Location not found")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Market Trends
print("\n3️⃣ Testing Market Trends Search...")
try:
    trends = get_market_trends("pickle business", "India")
    if trends:
        print("✅ Market trends working!")
        for i, trend in enumerate(trends[:2], 1):
            print(f"   {i}. {trend['title'][:50]}...")
    else:
        print("⚠️ No trends found")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Local Resources
print("\n4️⃣ Testing Local Resource Search (Full Integration)...")
try:
    resources = search_local_resources("food business", "Jaipur")
    if resources and not resources.get('error'):
        print("✅ Local resource search working!")
        print(f"   Location: {resources.get('location', 'N/A')}")
        print(f"   Suppliers found: {len(resources.get('suppliers', []))}")
        print(f"   Markets found: {len(resources.get('markets', []))}")
        print(f"   Training centers: {len(resources.get('training_centers', []))}")
        print(f"   Government offices: {len(resources.get('government_offices', []))}")
        
        if resources.get('suppliers'):
            print("\n   Sample suppliers:")
            for supplier in resources['suppliers'][:2]:
                print(f"   - {supplier['name']} ({supplier['distance_km']}km away)")
    else:
        print(f"⚠️ Resource search returned: {resources}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("\n🎉 Testing Complete!\n")
print("💡 Tips:")
print("   - Web search provides real-time scheme and trend data")
print("   - Location services find actual nearby businesses")
print("   - All services work without API keys (free APIs)")
print("   - Data freshness depends on OpenStreetMap contributors")
