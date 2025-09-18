"""
MongoEngine Document representing an owner/user entity.

Each Owner record stores basic identity information and relationships to
their snakes and cages. The related IDs are stored as lists on the Owner
document for simple ownership lookups.
"""
import datetime
import mongoengine

"""
Owner document stored in the 'owners' collection (db alias: 'core').

Fields:
    registered_date: When this owner account was created/registered. Defaults
        to the current time at document creation.
    name: Human-friendly display name of the owner (required).
    email: Contact email of the owner (required).
            Consider enforcing uniqueness and indexing in production.

    snake_ids: List of identifiers of snakes owned by this user.
    cage_ids: List of identifiers of cages owned by this user.

Notes:
    - DateTime default uses the callable (datetime.datetime.now) so each new
        document gets a fresh timestamp when created.
    - ListField without an inner field type accepts arbitrary values. If these
        lists are meant to store MongoDB ObjectIds, prefer:
            ListField(mongoengine.ObjectIdField())
    - Be consistent about timezone handling for registered_date (naive vs aware).
    - Consider adding indexes (e.g., on email) for faster lookups and deduplication.
"""
class Owner(mongoengine.Document):
    registered_date = mongoengine.DateTimeField(default=datetime.datetime.now) # Timestamp when the owner was registered; evaluated per-document at creation time.
    name = mongoengine.StringField(required=True) # Owner's display name (required).
    email = mongoengine.StringField(required=True) # Owner's email address (required). In production, consider unique=True and index=True.

    # Related entity identifiers (untyped lists; see notes above).
    snake_ids = mongoengine.ListField()
    cage_ids = mongoengine.ListField()

    # MongoEngine metadata: which DB alias/collection this document uses.
    meta = {
        'db_alias': 'core',
        'collection': 'owners'
    }
