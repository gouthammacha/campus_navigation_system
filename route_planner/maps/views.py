from django.shortcuts import render
import openrouteservice
import os
import json

API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
client = openrouteservice.Client(key=API_KEY)

waypoints = {
    "basketball court": (17.282128, 78.554006),
    "canteen": (17.281891, 78.553765),
    "mv block": (17.282433, 78.553351),
    "library": (17.282258, 78.553091),
    "sv block": (17.282838, 78.553278),
    "stationary": (17.283381, 78.553252),
    "beach volleyball": (17.282488, 78.553999),
    "cricket ground": (17.282633, 78.553839),
    "games block": (17.283233, 78.552779),
    "volleyball court": (17.283027, 78.552684),
    "small gate": (17.281913, 78.553885),
    "main gate": (17.280449, 78.553885),
}

def get_distance(loc1, loc2):
    """Calculate approximate distance using Euclidean method."""
    lat1, lon1 = waypoints[loc1]
    lat2, lon2 = waypoints[loc2]
    return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5

def get_route(coords):
    try:
        route = client.directions(
            coordinates=[(lon, lat) for lat, lon in coords],
            profile="foot-walking",
            format="geojson"
        )
        if route and "features" in route:
            return route["features"][0]["geometry"]["coordinates"]
    except openrouteservice.exceptions.ApiError as e:
        print(f"OpenRouteService API error: {e}")
    return None

def optimize_route(prev_dest, start1, start2, end1, end2):
    """Optimize route by ensuring the shortest path while maintaining existing functionality."""
    try:
        if not prev_dest:
            prev_dest = start1  # Default start if no previous destination

        # Determine nearest start location first
        start1_dist = get_distance(prev_dest, start1)
        start2_dist = get_distance(prev_dest, start2)
        if start1_dist < start2_dist:
            first_start, second_start = start1, start2
        else:
            first_start, second_start = start2, start1

        # Determine nearest destination first
        first_start_dest = end1 if first_start == start1 else end2
        second_start_dest = end1 if second_start == start1 else end2
        dest1_dist = get_distance(first_start, first_start_dest)
        dest2_dist = get_distance(second_start, second_start_dest)
        
        if dest1_dist < get_distance(first_start, second_start):
            ordered_route = [prev_dest, first_start, first_start_dest, second_start, second_start_dest]
        else:
            ordered_route = [prev_dest, first_start, second_start, first_start_dest, second_start_dest]

        return ordered_route
    except Exception as e:
        print(f"Route optimization error: {e}")
        return [prev_dest, start1, start2, end1, end2]  # Fallback order

def route_planner(request):
    locations = [loc.title() for loc in waypoints.keys()]
    prev_dest = request.session.get("last_location", None)

    start1 = request.GET.get("start1", "").lower()
    start2 = request.GET.get("start2", "").lower()
    end1 = request.GET.get("end1", "").lower()
    end2 = request.GET.get("end2", "").lower()

    selected_locations = [start1, start2, end1, end2]
    selected_locations = [loc for loc in selected_locations if loc in waypoints]  # Filter valid locations

    if len(selected_locations) == 4:
        optimized_route = optimize_route(prev_dest, start1, start2, end1, end2)
        route = get_route([waypoints[loc] for loc in optimized_route])
        request.session["last_location"] = optimized_route[-1]  # Store last destination
    else:
        route = []

    return render(request, "route_planner.html", {
        "locations": locations,
        "waypoints_json": json.dumps(waypoints),
        "route_json": json.dumps(route),
        "last_location": prev_dest
    })