"""
MongoEngine document for storing snakes.

This model maps to the 'snakes' collection in the database registered
under the 'core' connection alias. See your MongoEngine connection setup
(e.g., mongoengine.register_connection(alias='core', name='snake_bnb')).
"""

import datetime  # Standard library: used for timestamp defaults.
import mongoengine  # ODM for MongoDB.

"""
A snake listed in the application.

Fields:
    registered_date (datetime): When the record was created; defaults to now.
    species (str): The species of the snake (e.g., 'Python regius').
    length (float): The snake's length (units as used by the app).
    name (str): The snake's name.
    is_venomous (bool): Whether the snake is venomous.
"""
class Snake(mongoengine.Document):
    registered_date = mongoengine.DateTimeField(default=datetime.datetime.now) # Creation timestamp; passing the callable ensures "now" is evaluated at save/instantiate time.
    
    # Required string fields describing the snake.
    species = mongoengine.StringField(required=True)
    name = mongoengine.StringField(required=True)

    # Required characteristics.
    length = mongoengine.FloatField(required=True)
    is_venomous = mongoengine.BooleanField(required=True)

    # MongoEngine metadata:
    # - db_alias: which registered connection this document binds to.
    # - collection: the MongoDB collection name to store documents in.
    meta = {
        'db_alias': 'core',
        'collection': 'snakes'
    }
