import datetime
from dateutil import parser

from infrastructure.switchlang import switch
import program_hosts as hosts
import services.data_service as svc
from program_hosts import success_msg, error_msg
import infrastructure.state as state

"""
Guest-facing CLI workflow.

This module provides the interactive command loop and actions for guests:
- Account creation and login via hosts helpers.
- Managing snakes (add/view).
- Searching for available cages and booking them.
- Viewing existing bookings.

Conventions:
- Uses infrastructure.switchlang.switch for a case-like control flow.
- Uses infrastructure.state.active_account to determine authentication state.
- Delegates persistence and querying to services.data_service (svc).
- Uses program_hosts.success_msg / error_msg for user feedback styling.

Notes:
- Dates are parsed with dateutil.parser and treated as naive datetimes.
- Input parsing is intentionally lightweight; errors will propagate if
    input cannot be converted (e.g., float() / int()), matching the original behavior.
"""

"""
Entry point for the guest workflow loop.

Prints the welcome banner and available commands, then processes user
actions in a loop until the user switches mode or exits the app.
"""
def run():
    print(' ****************** Welcome guest **************** ')
    print()

    show_commands()

    # Main interactive loop.
    while True:
        # Reuse host's get_action() prompt which prefixes active account name if logged in.
        action = hosts.get_action()

        # switch() creates a context enabling s.case(...) branching on the provided action.
        with switch(action) as s:
            # Account actions handled by host module.
            s.case('c', hosts.create_account)
            s.case('l', hosts.log_into_account)

            # Guest-specific actions.
            s.case('a', add_a_snake)
            s.case('y', view_your_snakes)
            s.case('b', book_a_cage)
            s.case('v', view_bookings)
            
            # Switch back to main menu (mode change signal).
            s.case('m', lambda: 'change_mode')
            
            # Utilities/help/exit.
            s.case('?', show_commands)
            s.case('', lambda: None)
            s.case(['x', 'bye', 'exit', 'exit()'], hosts.exit_app)
            
            # Fallback when no case matched.
            s.default(hosts.unknown_command)

        # Reload any changes to the active account (e.g., after create/login or data changes).
        state.reload_account()

        if action:
            print()

        # If the case produced a mode change signal, return to caller (likely main menu).
        if s.result == 'change_mode':
            return

"""
Print the list of available commands for the guest workflow.
"""
def show_commands():
    print('What action would you like to take:')
    print('[C]reate an account')
    print('[L]ogin to your account')
    print('[B]ook a cage')
    print('[A]dd a snake')
    print('View [y]our snakes')
    print('[V]iew your bookings')
    print('[M]ain menu')
    print('e[X]it app')
    print('[?] Help (this info)')
    print()

"""
Collect snake details from the user and create it under the active account.

Requires an authenticated session (state.active_account).
"""
def add_a_snake():
    
    print(' ****************** Add a snake **************** ')
    if not state.active_account:
        error_msg("You must log in first to add a snake")
        return

    # Basic prompts; empty name cancels.
    name = input("What is your snake's name? ")
    if not name:
        error_msg('cancelled')
        return

    # The following will raise ValueError if the user does not enter a float; original behavior preserved.
    length = float(input('How long is your snake (in meters)? '))
    species = input("Species? ")

    # Treat any input starting with 'y' or 'Y' as True.
    is_venomous = input("Is your snake venomous [y]es, [n]o? ").lower().startswith('y')

    # Create the snake via the service layer and refresh local account state.
    snake = svc.add_snake(state.active_account, name, length, species, is_venomous)
    state.reload_account()
    success_msg('Created {} with id {}'.format(snake.name, snake.id))

"""
Display all snakes owned by the active account.
"""
def view_your_snakes():
    print(' ****************** Your snakes **************** ')
    if not state.active_account:
        error_msg("You must log in first to view your snakes")
        return

    # Fetch snakes by owner id; display key attributes.
    snakes = svc.get_snakes_for_user(state.active_account.id)
    print("You have {} snakes.".format(len(snakes)))
    for s in snakes:
        print(" * {} is a {} that is {}m long and is {}venomous.".format(
            s.name,
            s.species,
            s.length,
            '' if s.is_venomous else 'not '
        ))

"""
Walk the user through finding available cages and booking one for a selected snake.

Steps:
- Ensure user is logged in and has at least one snake.
- Collect check-in/out dates.
- Let the user select a snake.
- Query available cages for the timeframe and snake properties.
- Let the user select and book a cage.
"""
def book_a_cage():
    print(' ****************** Book a cage **************** ')
    if not state.active_account:
        error_msg("You must log in first to book a cage")
        return

    # Must have at least one snake to book a cage.
    snakes = svc.get_snakes_for_user(state.active_account.id)
    if not snakes:
        error_msg('You must first [a]dd a snake before you can book a cage.')
        return

    print("Let's start by finding available cages.")

    # Gather and parse dates; empty input cancels.
    start_text = input("Check-in date [yyyy-mm-dd]: ")
    if not start_text:
        error_msg('cancelled')
        return

    # dateutil.parser.parse provides flexible date parsing; naive datetimes are used in this app.
    checkin = parser.parse(start_text)
    checkout = parser.parse(input("Check-out date [yyyy-mm-dd]: "))

    # Basic validation: check-in must be strictly before check-out.
    if checkin >= checkout:
        error_msg('Check in must be before check out')
        return

    print()
    
    # Present the user's snakes for selection (1-based indexing for user friendliness).
    for idx, s in enumerate(snakes):
        print('{}. {} (length: {}, venomous: {})'.format(
            idx + 1,
            s.name,
            s.length,
            'yes' if s.is_venomous else 'no'
        ))

    # Convert user's 1-based choice to 0-based index; ValueError/IndexError may occur on bad input.
    snake = snakes[int(input('Which snake do you want to book (number)')) - 1]

    # Query cages that fit size, venomous constraints, and availability windows.
    cages = svc.get_available_cages(checkin, checkout, snake)

    print("There are {} cages available in that time.".format(len(cages)))
    for idx, c in enumerate(cages):
        print(" {}. {} with {}m carpeted: {}, has toys: {}.".format(
            idx + 1,
            c.name,
            c.square_meters,
            'yes' if c.is_carpeted else 'no',
            'yes' if c.has_toys else 'no'))

    if not cages:
        error_msg("Sorry, no cages are available for that date.")
        return

    # Select a cage and book it for the chosen window.
    cage = cages[int(input('Which cage do you want to book (number)')) - 1]
    svc.book_cage(state.active_account, snake, cage, checkin, checkout)

    success_msg('Successfully booked {} for {} at ${}/night.'.format(cage.name, snake.name, cage.price))

"""
Display all bookings for the active account, including cage names and durations.

Relies on svc.get_bookings_for_user(email) which returns booking subdocuments,
augmented with a dynamic 'cage' attribute referencing the parent cage.
"""
def view_bookings():    
    print(' ****************** Your bookings **************** ')
    if not state.active_account:
        error_msg("You must log in first to register a cage")
        return

    # Build a lookup from snake id to snake object for easy name resolution.
    snakes = {s.id: s for s in svc.get_snakes_for_user(state.active_account.id)}

    # Fetch bookings filtered by the active account's email.
    bookings = svc.get_bookings_for_user(state.active_account.email)

    print("You have {} bookings.".format(len(bookings)))
    for b in bookings:
        # noinspection PyUnresolvedReferences
        # The 'cage' attribute is attached at runtime in the data service for display convenience.
        print(' * Snake: {} is booked at {} from {} for {} days.'.format(
            snakes.get(b.guest_snake_id).name,
            b.cage.name,
            datetime.date(b.check_in_date.year, b.check_in_date.month, b.check_in_date.day),
            (b.check_out_date - b.check_in_date).days
        ))