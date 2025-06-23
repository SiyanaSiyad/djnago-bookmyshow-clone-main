from django.urls import path
from . import views
urlpatterns=[
    path('',views.movie_list,name='movie_list'),
    path('<int:movie_id>/theaters',views.theater_list,name='theater_list'),
    path('theater/<int:theater_id>/seats/book/',views.book_seats,name='book_seats'),
    path('showtimings/', views.show_timings, name='show_timings'),  # ⬅ new
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
]