"""
Application entry point for Snake BnB.

This module:
- Initializes the MongoEngine connection (via data.mongo_setup.global_init).
- Prints a stylized application header.
- Enters the main loop to determine user intent (guest vs host) and
  dispatches to the appropriate mode controller (program_guests or program_hosts).
"""

from colorama import Fore # Colored terminal text (foreground colors).
import program_guests # Guest-facing workflows (booking cages, etc.).
import program_hosts # Host-facing workflows (managing cages, bookings, etc.).
import data.mongo_setup as mongo_setup # MongoEngine connection setup (alias 'core' -> 'snake_bnb').

"""
Initialize the app and dispatch to guest/host flows in a loop.

Steps:
1) Initialize the database connection so models using db_alias='core' bind correctly.
2) Print the application header (title + ASCII art).
3) In a loop:
    - Ask the user whether they are a guest or a host.
    - Run the respective program flow until it returns (user switches mode or exits).
4) Exit gracefully on Ctrl+C (KeyboardInterrupt).
"""
def main():
    mongo_setup.global_init() # Register the MongoEngine connection alias 'core' for the 'snake_bnb' database.

    print_header() # Show the app header and welcome copy.

    try:
        # Main interaction loop: decide intent and delegate to the correct mode.
        while True:
            if find_user_intent() == 'book':
                program_guests.run() # Guest (book a cage) path.
            else:
                program_hosts.run() # Host (offer cage space) path.
    except KeyboardInterrupt:
        return # Allow clean termination with Ctrl+C without a stack trace.

"""Render the application banner and a short welcome message."""
def print_header():
    snake = \
        """
             ~8I?? OM               
            M..I?Z 7O?M             
            ?   ?8   ?I8            
           MOM???I?ZO??IZ           
          M:??O??????MII            
          OIIII$NI7??I$             
               IIID?IIZ             
  +$       ,IM ,~7??I7$             
I?        MM   ?:::?7$              
??              7,::?778+=~+??8       
??Z             ?,:,:I7$I??????+~~+    
??D          N==7,::,I77??????????=~$  
~???        I~~I?,::,77$Z?????????????  
???+~M   $+~+???? :::II7$II777II??????N 
OI??????????I$$M=,:+7??I$7I??????????? 
 N$$$ZDI      =++:$???????????II78  
               =~~:~~7II777$$Z      
                     ~ZMM~ """

    print(Fore.WHITE + '****************  SNAKE BnB  ****************')
    print(Fore.GREEN + snake)
    print(Fore.WHITE + '*********************************************')
    print()
    print("Welcome to Snake BnB!")
    print("Why are you here?")
    print()

"""
Ask the user whether they are a guest or a host and return an intent token.

Returns:
    str: 'book' for guests or 'offer' for hosts.
"""
def find_user_intent():
    print("[g] Book a cage for your snake")
    print("[h] Offer extra cage space")
    print()
    
    choice = input("Are you a [g]uest or [h]ost? ")
    
    # Host chooses 'h'; any other input defaults to guest 'book' flow to reduce friction.
    if choice == 'h':
        return 'offer'

    return 'book'

# Standard Python entry-point guard.
if __name__ == '__main__':
    main()