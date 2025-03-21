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

def optimize_route(locations):
    """Get the optimized order of waypoints for shortest travel distance."""
    try:
        response = client.optimization(
            jobs=[{"id": i, "location": [waypoints[loc][1], waypoints[loc][0]]} for i, loc in enumerate(locations)],
            vehicles=[{
                "id": 0,
                "profile": "foot-walking",
                "start": [waypoints[locations[0]][1], waypoints[locations[0]][0]],
                "end": [waypoints[locations[-1]][1], waypoints[locations[-1]][0]]
            }]
        )
        optimized_order = [locations[job["id"]] for job in sorted(response["routes"][0]["steps"], key=lambda x: x["arrival"])]
        return optimized_order
    except Exception as e:
        print(f"Route optimization error: {e}")
        return locations

def route_planner(request):
    locations = [loc.title() for loc in waypoints.keys()]
    last_location = request.session.get("last_location", None)

    selected_locations = [
        request.GET.get("start1", "").lower(),
        request.GET.get("start2", "").lower(),
        request.GET.get("end1", "").lower(),
        request.GET.get("end2", "").lower(),
    ]
    selected_locations = [loc for loc in selected_locations if loc in waypoints]

    if last_location and last_location in waypoints:
        selected_locations.insert(0, last_location)  # Start from last location

    if len(selected_locations) > 1:
        optimized_route = optimize_route(selected_locations)
        route = get_route([waypoints[loc] for loc in optimized_route])
        request.session["last_location"] = optimized_route[-1]  # Store the last visited location
    else:
        route = []

    return render(request, "route_planner.html", {
        "locations": locations,
        "waypoints_json": json.dumps(waypoints),
        "route_json": json.dumps(route),
        "last_location": last_location
    })
