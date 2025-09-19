"""Process-wide account state.

Exposes:
- active_account: Optional[Owner] - the current in-memory account (or None if no account is active).
- reload_account(): Refresh the in-memory active account from persistence using the email as the lookup key.

This helps keep the in-memory state synchronized with the latest data stored via services.data_service.
"""

from typing import Optional

from data.owners import Owner
import services.data_service as svc

# The currently active Owner instance for this process/session.
# None means no account is active (e.g., before login or after logout).
active_account: Optional[Owner] = None

"""Refresh the global active_account from the database, if one is set.

    Behavior:
    - If active_account is None, this is a no-op.
    - Otherwise, it re-queries by the account's email to obtain the latest persisted state.
    - If the account no longer exists in storage, the lookup will return None, and
      active_account will be set to None.
"""
def reload_account():
    global active_account  # We rebind the module-level variable below.
    if not active_account:
        return # Nothing to reload if there's no active account set.

    # Re-fetch the account from persistence using the current email.
    # This ensures we have the latest data (e.g., role/permissions/profile updates).
    active_account = svc.find_account_by_email(active_account.email)