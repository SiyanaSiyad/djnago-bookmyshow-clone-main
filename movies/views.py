from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta

def movie_list(request):
    search_query = request.GET.get('search')
    if search_query:
        movies = Movie.objects.filter(name__icontains=search_query)
    else:
        movies = Movie.objects.all()
    return render(request, 'movies/movie_list.html', {'movies': movies})


def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theater = Theater.objects.filter(movie=movie)
    return render(request, 'movies/theater_list.html', {'movie': movie, 'theaters': theater})


@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theaters = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theaters)

    total_seats = seats.count()
    available_seats = seats.filter(is_booked=False).count()

    if request.method == 'POST':
        selected_Seats = request.POST.getlist('seats')
        error_seats = []

        if not selected_Seats:
            return render(request, "movies/seat_selection.html", {
                'theaters': theaters,
                "seats": seats,
                'available_seats': available_seats,
                'total_seats': total_seats,
                'error': "No seat selected"
            })

        # --- Dynamic Pricing Logic ---
        demand_ratio = 1 - (available_seats / total_seats)  # e.g. 0.8 means 80% booked
        time_to_show = theaters.time - timezone.now()

        for seat_id in selected_Seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theaters)

            if seat.is_booked:
                error_seats.append(seat.seat_number)
                continue

            # Base price
            price = 150.00

            # If high demand, increase price
            if demand_ratio >= 0.7:  # 70% or more seats booked
                price += 50

            # If show starts in 2 hours or less, increase price
            if time_to_show <= timedelta(hours=2):
                price += 50

            # Final price updated
            seat.price = price
            seat.save()

            try:
                Booking.objects.create(
                    user=request.user,
                    seat=seat,
                    movie=theaters.movie,
                    theater=theaters
                )
                seat.is_booked = True
                seat.save()
            except IntegrityError:
                error_seats.append(seat.seat_number)

        if error_seats:
            error_message = f"The following seats are already booked: {', '.join(error_seats)}"
            return render(request, 'movies/seat_selection.html', {
                'theaters': theaters,
                "seats": seats,
                'available_seats': available_seats,
                'total_seats': total_seats,
                'error': error_message
            })

        return redirect('profile')

    return render(request, 'movies/seat_selection.html', {
        'theaters': theaters,
        "seats": seats,
        'available_seats': available_seats,
        'total_seats': total_seats
    })


# ------------------- Admin Dashboard ---------------------

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from .models import Booking, Movie, Theater
import json

@staff_member_required
def admin_dashboard(request):
    total_revenue = Booking.objects.aggregate(total=Sum('seat__price'))['total'] or 0

    # 📊 Top 5 Most Popular Movies
    popular_movies = Movie.objects.annotate(
        bookings_count=Count('booking')
    ).order_by('-bookings_count')[:5]

    # 🏢 Top 5 Busiest Theaters
    busy_theaters = Theater.objects.annotate(
        bookings_count=Count('booking')
    ).order_by('-bookings_count')[:5]

    # 🎯 Data for Pie Chart
    movie_labels = [movie.name for movie in popular_movies]
    movie_data = [movie.bookings_count for movie in popular_movies]

    # 📊 Data for Bar Chart
    theater_labels = [f"{theater.name} ({theater.movie.name})" for theater in busy_theaters]
    theater_data = [theater.bookings_count for theater in busy_theaters]

    # 📈 Monthly Revenue for Line Chart
    monthly_bookings = Booking.objects.annotate(month=TruncMonth('booked_at')) \
                                      .values('month') \
                                      .annotate(total=Sum('seat__price')) \
                                      .order_by('month')

    month_labels = []
    revenue_data = []
    for entry in monthly_bookings:
        month_name = entry['month'].strftime('%B')
        month_labels.append(month_name)
        revenue_data.append(float(entry['total'])) 

    return render(request, 'movies/admin_dashboard.html', {
        'total_revenue': total_revenue,
        'popular_movies': popular_movies,
        'busy_theaters': busy_theaters,
        'movie_labels': json.dumps(movie_labels),
        'movie_data': json.dumps(movie_data),
        'theater_labels': json.dumps(theater_labels),
        'theater_data': json.dumps(theater_data),
        'month_labels': json.dumps(month_labels),
        'revenue_data': json.dumps(revenue_data),
    })



def show_timings(request):
    movies = Movie.objects.prefetch_related('theaters').all()
    return render(request, 'movies/show_timings.html', {'movies': movies})
