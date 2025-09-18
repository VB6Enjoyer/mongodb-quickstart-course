"""
MongoEngine EmbeddedDocument representing a single reservation (booking).

This model is designed to be embedded inside a parent document (e.g., Cage).
Storing bookings as embedded documents keeps booking data co-located with the
parent for efficient reads when accessing a cage and its reservations together.
"""
import mongoengine

"""
A single reservation made by an owner for a specific snake.

    Fields:
        guest_owner_id: ObjectId of the user/owner who made the booking.
        guest_snake_id: ObjectId of the snake being boarded.

        booked_date: When this booking record was created (optional).
        check_in_date: Start date/time of the stay (required).
        check_out_date: End date/time of the stay (required).

        review: Free-form text feedback left by the owner (optional).
        rating: Numeric rating for the stay (default 0). Define a convention
                (e.g., 0–5) at the application level.

    Notes:
    - ObjectIdField is used instead of ReferenceField because this document
        is embedded; storing raw ObjectIds avoids cross-collection references
        and simplifies the embedded schema.
    - Ensure that check_in_date and check_out_date use consistent timezone
        handling (both naive or both aware) to avoid arithmetic issues.
"""
class Booking(mongoengine.EmbeddedDocument):
    # Identifiers of related entities (stored as raw ObjectIds).
    guest_owner_id = mongoengine.ObjectIdField()
    guest_snake_id = mongoengine.ObjectIdField()

    # Timestamps for the booking lifecycle.
    booked_date = mongoengine.DateTimeField()
    check_in_date = mongoengine.DateTimeField(required=True)
    check_out_date = mongoengine.DateTimeField(required=True)

    # Optional feedback fields.
    review = mongoengine.StringField()
    rating = mongoengine.IntField(default=0)

    """
    Return the whole number of days between check-in and check-out.

    This uses datetime.timedelta.days, which:
        - Truncates partial days (e.g., 1 day 23 hours -> 1).
        - Can be negative if check_out_date < check_in_date.

    If you need rounding up or exact fractional days, adjust the logic
    at the application layer accordingly.
    """
    @property
    def duration_in_days(self):
        dt = self.check_out_date - self.check_in_date
        return dt.days
