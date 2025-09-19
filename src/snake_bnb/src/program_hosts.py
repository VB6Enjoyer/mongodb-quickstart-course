import datetime
from colorama import Fore
from dateutil import parser

from infrastructure.switchlang import switch
import infrastructure.state as state
import services.data_service as svc


"""
Host-facing CLI workflow.

This module provides the interactive command loop and actions for hosts:
- Account creation and login.
- Registering cages and listing them.
- Managing availability windows for cages.
- Viewing bookings made by guests.

Conventions:
- Uses infrastructure.switchlang.switch for a case-like control flow pattern.
- Uses infrastructure.state.active_account to determine authentication state and identity.
- Delegates persistence, validation, and querying to services.data_service (svc).
- Uses success_msg / error_msg helpers for colored user feedback.

Notes:
- Dates are parsed with dateutil.parser and treated as naive datetimes.
- Input parsing is intentionally lightweight and can raise errors
  (e.g., float()/int() conversions) to preserve the original behavior.
"""

"""
Entry point for the host workflow loop.

Prints a banner and available commands, then processes user input in a loop
until the user switches mode or exits the app.
"""
def run():
    print(' ****************** Welcome host **************** ')
    print()

    show_commands()

    # Main interactive loop.
    while True:
        # Prompts use the active account name prefix when logged in.
        action = get_action()

        # switch() yields a context manager enabling case-style branching.
        with switch(action) as s:
            s.case('c', create_account)
            s.case('a', create_account)  # Alias for create account.
            s.case('l', log_into_account)
            s.case('y', list_cages)
            s.case('r', register_cage)
            s.case('u', update_availability)
            s.case('v', view_bookings)
            s.case('m', lambda: 'change_mode')  # Signal to return to main mode selector.
            s.case(['x', 'bye', 'exit', 'exit()'], exit_app)
            s.case('?', show_commands)
            s.case('', lambda: None)  # No-op for empty input.
            s.default(unknown_command)

        # Cosmetic spacing after actions.
        if action:
            print()

        # If mode change was requested, return to caller (likely main menu).
        if s.result == 'change_mode':
            return

"""
Print the list of available commands for host operations.
"""
def show_commands():
    print('What action would you like to take:')
    print('[C]reate an [a]ccount')
    print('[L]ogin to your account')
    print('List [y]our cages')
    print('[R]egister a cage')
    print('[U]pdate cage availability')
    print('[V]iew your bookings')
    print('Change [M]ode (guest or host)')
    print('e[X]it app')
    print('[?] Help (this info)')
    print()


"""
Create a new host account after verifying the email isn't already in use.

Side effects:
- Sets state.active_account upon successful creation.
- Prints a success or error message accordingly.
"""
def create_account():
    print(' ****************** REGISTER **************** ')

    name = input('What is your name? ')
    email = input('What is your email? ').strip().lower() # Normalize email for consistent lookups (lowercase, trimmed).

    # Ensure email uniqueness at the application level (not DB-enforced here).
    old_account = svc.find_account_by_email(email)
    if old_account:
        error_msg(f"ERROR: Account with email {email} already exists.")
        return

    # Create and persist the account via the service layer.
    state.active_account = svc.create_account(name, email)
    success_msg(f"Created new account with id {state.active_account.id}.")

"""
Log into an existing host account using an email address.

Side effects:
- Sets state.active_account on success.
"""
def log_into_account():
    print(' ****************** LOGIN **************** ')

    email = input('What is your email? ').strip().lower()
    account = svc.find_account_by_email(email)

    if not account:
        error_msg(f'Could not find account with email {email}.')
        return

    state.active_account = account
    success_msg('Logged in successfully.')

"""
Collect cage details from the host and register the cage.

Requires an authenticated session (state.active_account).
The function prompts for cage attributes and persists the new cage, linking
it to the active account.

Side effects:
- Persists a new cage document.
- Updates the active account's managed cages.
- Reloads local account state to reflect changes.
"""
def register_cage():
    
    print(' ****************** REGISTER CAGE **************** ')

    if not state.active_account:
        error_msg('You must login first to register a cage.')
        return

    # Early cancel if meters input is empty.
    meters = input('How many square meters is the cage? ')
    if not meters:
        error_msg('Cancelled')
        return

    # Basic property collection; conversions can raise ValueError if invalid.
    meters = float(meters)
    carpeted = input("Is it carpeted [y, n]? ").lower().startswith('y')
    has_toys = input("Have snake toys [y, n]? ").lower().startswith('y')
    allow_dangerous = input("Can you host venomous snakes [y, n]? ").lower().startswith('y')
    name = input("Give your cage a name: ")
    price = float(input("How much are you charging?  "))

    # Delegate creation to the service layer; it links the cage to the owner.
    cage = svc.register_cage(
        state.active_account, name,
        allow_dangerous, has_toys, carpeted, meters, price
    )

    # Refresh the in-memory account to include the new cage id.
    state.reload_account()
    success_msg(f'Register new cage with id {cage.id}.')

"""
List all cages for the active account, including their bookings.

Parameters:
- suppress_header: When True, omits the banner header (useful when called
    as a step within other flows like update_availability()).
"""
def list_cages(suppress_header=False):
    if not suppress_header:
        print(' ******************     Your cages     **************** ')

    if not state.active_account:
        error_msg('You must login first to register a cage.')
        return

    # Fetch cages managed by the active account.
    cages = svc.find_cages_for_user(state.active_account)
    print(f"You have {len(cages)} cages.")
    for idx, c in enumerate(cages):
        print(f' {idx + 1}. {c.name} is {c.square_meters} meters.')
        # Print each booking with date window and booking status.
        for b in c.bookings:
            print('      * Booking: {}, {} days, booked? {}'.format(
                b.check_in_date,
                (b.check_out_date - b.check_in_date).days,
                'YES' if b.booked_date is not None else 'no'
            ))

"""
Add an availability window to one of the host's cages.

Workflow:
- Ensure the user is logged in.
- Show cages and prompt for a selection (by number).
- Prompt for start date and duration.
- Persist the new availability window via the service layer.
"""
def update_availability():
    print(' ****************** Add available date **************** ')

    if not state.active_account:
        error_msg("You must log in first to register a cage")
        return

    # Present cages with indices for selection.
    list_cages(suppress_header=True)

    cage_number = input("Enter cage number: ")
    if not cage_number.strip():
        error_msg('Cancelled')
        print()
        return

    # Convert user-friendly 1-based index to 0-based list index.
    cage_number = int(cage_number)

    cages = svc.find_cages_for_user(state.active_account)
    selected_cage = cages[cage_number - 1]

    success_msg("Selected cage {}".format(selected_cage.name))

    # Parse start date using dateutil.parser for flexibility.
    start_date = parser.parse(
        input("Enter available date [yyyy-mm-dd]: ")
    )
    days = int(input("How many days is this block of time? "))

    # Persist availability as an embedded booking block.
    svc.add_available_date(
        selected_cage,
        start_date,
        days
    )

    success_msg(f'Date added to cage {selected_cage.name}.')

"""
Display all bookings (already reserved windows) across the host's cages.

Only bookings with a non-null booked_date are shown.
"""
def view_bookings():
    print(' ****************** Your bookings **************** ')

    if not state.active_account:
        error_msg("You must log in first to register a cage")
        return

    # Collect all cages managed by the host.
    cages = svc.find_cages_for_user(state.active_account)

    # Flatten all booked bookings across cages.
    bookings = [
        (c, b)
        for c in cages
        for b in c.bookings
        if b.booked_date is not None
    ]

    print("You have {} bookings.".format(len(bookings)))
    for c, b in bookings:
        # Print a concise summary; duration_in_days is assumed provided by the booking model.
        print(' * Cage: {}, booked date: {}, from {} for {} days.'.format(
            c.name,
            datetime.date(b.booked_date.year, b.booked_date.month, b.booked_date.day),
            datetime.date(b.check_in_date.year, b.check_in_date.month, b.check_in_date.day),
            b.duration_in_days
        ))

"""
Exit the application by raising KeyboardInterrupt.

This is caught by the outer runtime to terminate gracefully.
"""
def exit_app():
    
    print()
    print('bye')
    raise KeyboardInterrupt()

"""
Prompt for the next action, using the active account name as a prefix if logged in.

Returns:
    The normalized command string (lowercased and stripped).
"""
def get_action():
    text = '> '
    if state.active_account:
        text = f'{state.active_account.name}> '

    # Set prompt to yellow; revert to white after input.
    action = input(Fore.YELLOW + text + Fore.WHITE)
    return action.strip().lower()

"""
Fallback handler for unrecognized commands.
"""
def unknown_command():
    print("Sorry we didn't understand that command.")

"""
Print a success message in green.
"""
def success_msg(text):
    print(Fore.LIGHTGREEN_EX + text + Fore.WHITE)

"""
Print an error message in red.
"""
def error_msg(text):
    print(Fore.LIGHTRED_EX + text + Fore.WHITE)