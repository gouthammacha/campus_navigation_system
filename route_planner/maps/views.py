import json
import os
import itertools
from django.shortcuts import render
import openrouteservice

API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
client = openrouteservice.Client(key=API_KEY)

waypoints = {
    "Basketball Court": (17.282128, 78.554006),
    "Canteen": (17.281891, 78.553765),
    "MV Block": (17.282433, 78.553351),
    "Library": (17.282258, 78.553091),
    "SV Block": (17.282838, 78.553278),
    "Stationary": (17.283381, 78.553252),
    "Beach Volleyball": (17.282488, 78.553999),
    "Cricket Ground": (17.282633, 78.553839),
    "Sports Block": (17.283233, 78.552779),
    "Volleyball Court": (17.283027, 78.552684),
    "Small Gate": (17.281913, 78.553885),
    "Main Gate": (17.280449, 78.553885),
}

ROUTE_HISTORY_FILE = "route_history.json"

def load_route_history():
    """Load previously tested paths from a file."""
    if os.path.exists(ROUTE_HISTORY_FILE):
        with open(ROUTE_HISTORY_FILE, "r") as file:
            return json.load(file)
    return {}

def save_route_history(history):
    """Save tested paths to a file."""
    with open(ROUTE_HISTORY_FILE, "w") as file:
        json.dump(history, file, indent=4)

def get_distance(loc1, loc2):
    """Calculate approximate Euclidean distance."""
    lat1, lon1 = waypoints[loc1]
    lat2, lon2 = waypoints[loc2]
    return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5

def get_route(coords, start, end):
    """Retrieve route; check learned paths first, then API."""
    history = load_route_history()
    key = f"{start}_{end}"
    
    # If route already exists in history, use it
    if key in history:
        return history[key]
    
    try:
        route = client.directions(
            coordinates=[(lon, lat) for lat, lon in coords],
            profile="foot-walking",
            format="geojson"
        )
        if route and "features" in route:
            path = route["features"][0]["geometry"]["coordinates"]
            history[key] = path  # Save new route
            save_route_history(history)
            return path
    except openrouteservice.exceptions.ApiError as e:
        print(f"OpenRouteService API error: {e}")
    
    return None

def calculate_total_distance(route):
    """Calculate the total distance of a route (from the previous destination)."""
    total_distance = 0
    for i in range(len(route) - 1):
        total_distance += get_distance(route[i], route[i + 1])
    return total_distance

def optimize_route(prev_dest, start1, start2, end1, end2):
    """Optimize the route by ensuring the shortest path considering all permutations."""
    try:
        # Define the locations to be included in the route
        locations = [start1, start2, end1, end2]
        
        # Ensure the previous destination is not None, defaulting to start1 if None
        if not prev_dest:
            prev_dest = start1

        # Generate all permutations of the locations
        possible_routes = itertools.permutations(locations)

        # Add the previous destination to each permutation for comparison
        all_routes = [(prev_dest,) + route for route in possible_routes]

        # Find the route with the minimum total distance
        min_route = None
        min_distance = float('inf')

        for route in all_routes:
            total_distance = calculate_total_distance(route)
            if total_distance < min_distance:
                min_distance = total_distance
                min_route = route

        return min_route

    except Exception as e:
        print(f"Route optimization error: {e}")
        return [prev_dest, start1, start2, end1, end2]  # Fallback to the original order if error occurs


def route_planner(request):
    locations = [loc.title() for loc in waypoints.keys()]
    prev_dest = request.session.get("last_location", None)

    start1 = request.GET.get("start1", "").lower()
    start2 = request.GET.get("start2", "").lower()
    end1 = request.GET.get("end1", "").lower()
    end2 = request.GET.get("end2", "").lower()

    selected_locations = [start1, start2, end1, end2]
    selected_locations = [loc for loc in selected_locations if loc in waypoints]

    if len(selected_locations) == 4:
        optimized_route = optimize_route(prev_dest, start1, start2, end1, end2)
        route = get_route([waypoints[loc] for loc in optimized_route], optimized_route[0], optimized_route[-1])
        request.session["last_location"] = optimized_route[-1]  # Store last destination
    else:
        route = []

    return render(request, "route_planner.html", {
        "locations": locations,
        "waypoints_json": json.dumps(waypoints),
        "route_json": json.dumps(route),
        "last_location": prev_dest
    })
