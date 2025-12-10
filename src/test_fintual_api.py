import requests
import json

def test_fintual_access(asset_id):
    # Try the standard endpoint found in docs/repos
    # Endpoint: https://fintual.cl/api/real_assets/{id}/days
    # This usually returns daily NAV (price)
    
    url = f"https://fintual.cl/api/real_assets/{asset_id}/days"
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("Success! Data received.")
            # Print structure of first item
            if 'data' in data and len(data['data']) > 0:
                print("Sample item:", json.dumps(data['data'][0], indent=2))
                print(f"Total days fetched: {len(data['data'])}")
                return True
            else:
                print("Response json structure unexpected or empty.")
                print(json.dumps(data, indent=2))
        else:
            print(f"Failed with status code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")
    return False

if __name__ == "__main__":
    # Test with Risky Norris (186)
    test_fintual_access(186)
