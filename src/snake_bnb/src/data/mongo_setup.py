import mongoengine # Import the MongoEngine library used to define models and manage MongoDB connections.

"""
Initialize MongoEngine and register the application's default connection.

- Registers a connection alias named 'core' that points to the 'snake_bnb' database.
- Call this once during application startup before importing/using models that
    specify `meta = {'db_alias': 'core'}` so they bind to this connection.
"""
def global_init():
    mongoengine.register_connection(alias='core', name='snake_bnb') # Create/register a named connection alias 'core' bound to the 'snake_bnb' database.