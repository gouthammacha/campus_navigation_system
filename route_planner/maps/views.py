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

def optimize_route(prev_dest, start1, start2, end1, end2):
    """Optimize route by considering the previous destination and efficient drop-offs."""
    try:
        locations = [start1, start2, end1, end2]
        if prev_dest:
            locations.insert(0, prev_dest)  # Start from previous destination if available

        response = client.optimization(
            jobs=[
                {"id": i, "location": [waypoints[loc][1], waypoints[loc][0]], "priority": 1 if i < 2 else 0}
                for i, loc in enumerate(locations)
            ],
            vehicles=[{
                "id": 0,
                "profile": "foot-walking",
                "start": [waypoints[locations[0]][1], waypoints[locations[0]][0]],
                "capacity": [2],  # Can carry both passengers
                "skills": [1],
            }]
        )

        # Get optimized order
        ordered_locations = [locations[job["id"]] for job in sorted(response["routes"][0]["steps"], key=lambda x: x["arrival"])]

        # Ensure intermediate drop-off if needed
        optimized_order = []
        picked_up = set()

        for i, loc in enumerate(ordered_locations):
            if loc in (start1, start2):  
                picked_up.add(loc)  # Mark pickup as done
            elif loc in (end1, end2):  
                if (start1 in picked_up and loc == end1) or (start2 in picked_up and loc == end2):
                    optimized_order.append(loc)  # Drop if picked up
            optimized_order.append(loc)  

        return optimized_order

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
