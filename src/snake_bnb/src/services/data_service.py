from typing import List, Optional

import datetime

import bson

from data.bookings import Booking
from data.cages import Cage
from data.owners import Owner
from data.snakes import Snake

"""
Service-layer helpers for creating and querying domain entities using MongoEngine.

Notes:
- All persistence is done immediately via .save() on MongoEngine documents.
- This module works with naive datetimes (no tzinfo). Ensure consistent usage
  across the app; consider timezone-aware datetimes in production.
- Relationships are stored via ObjectId references:
  - Owner.cage_ids: List of Cage ids the owner manages.
  - Owner.snake_ids: List of Snake ids owned by the owner.
  - Cage.bookings: Embedded list of Booking subdocuments.
"""

"""
Create and persist a new Owner account.

Parameters:
    name: Display name for the owner.
    email: Contact email (not enforced unique here).

Returns:
    The newly created and persisted Owner document.
"""
def create_account(name: str, email: str) -> Owner:
    
    owner = Owner()
    owner.name = name
    owner.email = email

    owner.save()  # Persist to the 'owners' collection.

    return owner

"""
Find the first Owner by email.

Parameters:
    email: The email to search for.

Returns:
    The first matching Owner or None if not found.
"""
def find_account_by_email(email: str) -> Owner:
    owner = Owner.objects(email=email).first()
    return owner

"""
Create a new Cage, persist it, and associate it to the active_account.

Parameters:
    active_account: The Owner who is registering the cage.
    name: Human-readable cage name.
    allow_dangerous: If True, cage can host venomous/dangerous snakes.
    has_toys: Enrichment/toys available.
    carpeted: Whether cage has carpet flooring.
    meters: Size of the cage in square meters.
    price: Price per rental period (ensure consistent units app-wide).

Returns:
    The newly created Cage document.
"""
def register_cage(active_account: Owner,
                  name, allow_dangerous, has_toys,
                  carpeted, meters, price) -> Cage:
    cage = Cage()

    # Set cage characteristics.
    cage.name = name
    cage.square_meters = meters
    cage.is_carpeted = carpeted
    cage.has_toys = has_toys
    cage.allow_dangerous_snakes = allow_dangerous
    cage.price = price

    cage.save()  # Persist the cage first to get an id.

    # Link the cage to the owner's list of managed cages.
    account = find_account_by_email(active_account.email)
    account.cage_ids.append(cage.id)
    account.save()

    return cage

"""
Retrieve all Cage documents associated with the provided Owner.

Parameters:
    account: The owner whose cages to fetch.

Returns:
    A list of Cage documents whose ids are in account.cage_ids.
"""
def find_cages_for_user(account: Owner) -> List[Cage]:
    query = Cage.objects(id__in=account.cage_ids)
    cages = list(query)  # Force evaluation; materialize into list.

    return cages

"""
Add an availability window (as a Booking) to a Cage.

The booking is considered available if guest_owner_id / guest_snake_id
remain unset (None).

Parameters:
    cage: The Cage to add availability to.
    start_date: Start of the availability window (check-in).
    days: Number of days from start_date for check-out.

Returns:
    The refreshed Cage document after persisting the new availability.
"""
def add_available_date(cage: Cage,
                       start_date: datetime.datetime, days: int) -> Cage:
    
    booking = Booking()
    booking.check_in_date = start_date
    booking.check_out_date = start_date + datetime.timedelta(days=days)

    # Re-fetch the cage to ensure we append to the most recent state/document.
    cage = Cage.objects(id=cage.id).first()
    cage.bookings.append(booking)
    cage.save()

    return cage

"""
Create a new Snake for the given owner and persist it.

Parameters:
    account: The Owner to associate the snake with.
    name: Snake's given name.
    length: Snake length (ensure consistent measurement units app-wide).
    species: Species string.
    is_venomous: Whether the snake is venomous.

Returns:
    The newly created Snake document.
"""
def add_snake(account, name, length, species, is_venomous) -> Snake:
    snake = Snake()
    snake.name = name
    snake.length = length
    snake.species = species
    snake.is_venomous = is_venomous
    snake.save()

    # Link the snake to the owner.
    owner = find_account_by_email(account.email)
    owner.snake_ids.append(snake.id)
    owner.save()

    return snake

"""
Retrieve all Snakes for an owner by their id.

Parameters:
    user_id: Owner's ObjectId.

Returns:
    A list of Snake documents whose ids are in Owner.snake_ids.
"""
def get_snakes_for_user(user_id: bson.ObjectId) -> List[Snake]:
    
    owner = Owner.objects(id=user_id).first()
    snakes = Snake.objects(id__in=owner.snake_ids).all()

    return list(snakes)

"""
Find cages that are available for a given date range and snake.

Availability criteria:
- Cage size must be >= snake.length / 4.
- The cage must have at least one Booking window such that:
    booking.check_in_date <= checkin and
    booking.check_out_date >= checkout and
    booking.guest_snake_id is None (unbooked/available).
- If the snake is venomous, the cage must allow dangerous snakes.

Parameters:
    checkin: Desired check-in datetime.
    checkout: Desired check-out datetime.
    snake: The Snake requiring a cage.

Returns:
    A list of cages available for the given parameters, roughly ordered by
    ascending price and then descending square_meters.
"""
def get_available_cages(checkin: datetime.datetime,
                        checkout: datetime.datetime, snake: Snake) -> List[Cage]:
    min_size = snake.length / 4

    # Initial server-side filters; embedded bookings date bounds are used to reduce candidates.
    query = Cage.objects() \
        .filter(square_meters__gte=min_size) \
        .filter(bookings__check_in_date__lte=checkin) \
        .filter(bookings__check_out_date__gte=checkout)

    if snake.is_venomous:
        query = query.filter(allow_dangerous_snakes=True)

    # Order: cheaper first, then larger (for same price).
    cages = query.order_by('price', '-square_meters')

    # Client-side check to ensure we only return cages that have an actually free booking window.
    final_cages = []
    for c in cages:
        for b in c.bookings:
            if b.check_in_date <= checkin and b.check_out_date >= checkout and b.guest_snake_id is None:
                final_cages.append(c)
                break  # Avoid adding the same cage multiple times.
    # Note: No deduping needed because we break on the first match per cage.

    return final_cages

"""
Book a cage by assigning an availability window to a specific owner and snake.

This function looks for an existing availability window on the given cage
that fully covers [checkin, checkout] and is currently unbooked. If found,
it marks it as booked by setting guest_owner_id, guest_snake_id, and booked_date.

Parameters:
    account: The Owner making the booking.
    snake: The Snake to be housed.
    cage: The Cage being booked.
    checkin: Desired check-in datetime.
    checkout: Desired check-out datetime.

Side Effects:
    - Modifies the embedded Booking within the Cage.
    - Persists the Cage with the updated booking.

Important:
    - This function assumes an appropriate availability window exists.
        If not found, 'booking' remains None and subsequent attribute
        access will raise an exception. Consider handling the None case
        and returning a status/result in higher-level code.
    - Datetimes are naive; ensure consistent timezone strategy across the app.
"""
def book_cage(account, snake, cage, checkin, checkout):
    booking: Optional[Booking] = None

    # Locate a suitable availability window.
    for b in cage.bookings:
        if b.check_in_date <= checkin and b.check_out_date >= checkout and b.guest_snake_id is None:
            booking = b
            break

    # WARNING: booking may be None if no availability matches.
    booking.guest_owner_id = account.id
    booking.guest_snake_id = snake.id
    booking.check_in_date = checkin
    booking.check_out_date = checkout
    booking.booked_date = datetime.datetime.now()  # Timestamp the booking action.

    cage.save()  # Persist the updated bookings on the cage.

"""
Get all bookings (as Booking subdocuments) that belong to the owner identified by email.

The returned Booking objects are augmented at runtime with a 'cage' attribute
linking back to their parent Cage for convenience in presentation layers.

Parameters:
    email: Owner's email address.

Returns:
    A list of Booking objects with an additional 'cage' attribute referring
    to the Cage they belong to.
"""
def get_bookings_for_user(email: str) -> List[Booking]:
    account = find_account_by_email(email)

    # Fetch cages that have at least one booking made by this account.
    # .only reduces payload to just 'bookings' and 'name' fields of the cage.
    booked_cages = Cage.objects() \
        .filter(bookings__guest_owner_id=account.id) \
        .only('bookings', 'name')

    def map_cage_to_booking(cage, booking):
        # Mutate the booking subdocument to include a back-reference for ease of use.
        booking.cage = cage
        return booking

    # Extract bookings belonging to this owner from each matching cage.
    bookings = [
        map_cage_to_booking(cage, booking)
        for cage in booked_cages
        for booking in cage.bookings
        if booking.guest_owner_id == account.id
    ]

    return bookings