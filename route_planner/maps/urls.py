from django.urls import path
from .views import route_planner
from django.urls import path
from . import views


urlpatterns = [
    path("", route_planner, name="route"),
    path("route_planner/", route_planner, name="route"),
    path('route_planner/', route_planner, name='route_planner'), 
    path('route_planner/', views.route_planner, name='route_planner'),
    # Other paths...
]
