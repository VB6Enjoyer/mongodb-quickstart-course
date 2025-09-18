"""
MongoEngine model representing a snake boarding cage.

Each Cage document describes a rentable cage with its attributes and a list of
embedded Booking records that capture reservations for that cage.
"""

import datetime
import mongoengine

# Embedded document representing a single booking/reservation for a cage.
# See data.bookings.Booking for details on fields like check-in/out, rating, etc.
from data.bookings import Booking

"""
Cage document stored in the 'cages' collection of the 'core' database alias.

Fields:
        registered_date: When this cage was registered in the system.
        name: Human-friendly name/identifier of the cage.
        price: Price per day (or other unit) to rent the cage.
        square_meters: Size of the cage in square meters.
        is_carpeted: Whether the cage has carpet flooring.
        has_toys: Whether the cage includes toys/enrichment items.
        allow_dangerous_snakes: Whether dangerous species are allowed in this cage.
        bookings: List of embedded Booking documents associated with this cage.
"""
class Cage(mongoengine.Document):
    # Timestamp when the cage was added to the system; defaults to "now" at creation time.
    # Passing the callable (without parentheses) ensures the time is evaluated per document.
    registered_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    name = mongoengine.StringField(required=True) # Descriptive name for the cage (required).
    price = mongoengine.FloatField(required=True) # Price per rental period (float, required). Interpret units consistently across the app.
    square_meters = mongoengine.FloatField(required=True) # Physical size of the cage in square meters (required).
    is_carpeted = mongoengine.BooleanField(required=True) # Whether the cage has carpet flooring (required).
    has_toys = mongoengine.BooleanField(required=True) # Whether the cage includes toys/enrichment (required).
    allow_dangerous_snakes = mongoengine.BooleanField(default=False) # If True, this cage can be booked for dangerous snakes; defaults to False for safety.

    # Embedded list of bookings tied to this cage.
    # Using EmbeddedDocumentListField keeps booking data co-located with the cage document.
    # With EmbeddedDocumentListField, each Cage document contains an array of embedded Booking subdocuments.
    bookings = mongoengine.EmbeddedDocumentListField(Booking)

    # MongoEngine metadata: which database alias and collection this document uses.
    meta = {
        'db_alias': 'core',       # Must match a configured connection alias in the app setup.
        'collection': 'cages'     # Collection name within the 'core' database.
    }
