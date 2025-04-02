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
    """Optimizes the route dynamically for an autonomous vehicle in a campus:
    - Picks up passengers from start locations before reaching destinations.
    - If a destination is on the way to another start location, visit it first.
    - Ensures shortest path selection at every step to minimize unnecessary backtracking.
    """
    try:
        if not prev_dest:
            prev_dest = start1  # Default start if no previous destination

        # Store locations and their respective destinations
        locations = {start1: end1, start2: end2}
        visited = set()
        route = [prev_dest]
        current_location = prev_dest
        remaining_starts = [start1, start2]
        remaining_destinations = [end1, end2]

        # Remove duplicate entries if start1 == end2 or start2 == end1
        if start1 == end2:
            remaining_destinations.remove(end2)
        if start2 == end1:
            remaining_destinations.remove(end1)

        # Step 1: Visit all start locations first
        while remaining_starts:
            # Choose the nearest start location
            remaining_starts.sort(key=lambda loc: get_distance(current_location, loc))
            next_start = remaining_starts.pop(0)
            route.append(next_start)
            visited.add(next_start)
            destination = locations[next_start]
            current_location = next_start  # Move to start location

            # Step 3: If the destination is on the way to the next start, visit it
            if remaining_starts:
                next_possible_start = remaining_starts[0]
                if (destination in remaining_destinations and
                    get_distance(current_location, destination) < get_distance(current_location, next_possible_start) and
                    get_distance(destination, next_possible_start) < get_distance(current_location, next_possible_start)):
                    
                    # Visit the destination first if it is on the way
                    route.append(destination)
                    visited.add(destination)
                    current_location = destination
                    remaining_destinations.remove(destination)

        # Step 4: Visit remaining destinations ensuring no backtracking
        while remaining_destinations:
            # Choose the nearest destination
            remaining_destinations.sort(key=lambda loc: get_distance(current_location, loc))
            next_dest = remaining_destinations.pop(0)

            # If another destination is on the way, visit it first
            if remaining_destinations:
                possible_next_dest = remaining_destinations[0]
                if (get_distance(current_location, next_dest) < get_distance(current_location, possible_next_dest) and
                    get_distance(next_dest, possible_next_dest) < get_distance(current_location, possible_next_dest)):
                    
                    # If next_dest is on the way to possible_next_dest, visit it first
                    route.append(next_dest)
                    visited.add(next_dest)
                    current_location = next_dest
                    remaining_destinations.remove(next_dest)

            # Finally, visit the next destination
            if next_dest not in visited:
                route.append(next_dest)
                visited.add(next_dest)
                current_location = next_dest

        return route
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