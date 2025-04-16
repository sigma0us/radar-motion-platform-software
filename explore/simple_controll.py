from ticlib import TicUSB  
from time import sleep  

def print_registers(tic):  
    print("=== Tic Registers ===")  
    print(f"Current position: {tic.get_current_position()}")  
    print(f"Target position: {tic.get_target_position()}")  
    print(f"Current velocity: {tic.get_current_velocity()}")  
    print(f"Max speed: {tic.get_max_speed()}")  
    print(f"Starting speed: {tic.get_starting_speed()}")  
    print(f"Max acceleration: {tic.get_max_acceleration()}")  
    print(f"Max deceleration: {tic.get_max_deceleration()}")  
    print(f"Error status: {tic.get_error_status()}")  
    print(f"Operation state: {tic.get_operation_state()}")  
    print(f"Auto driver error: {tic.settings.get_auto_clear_driver_error()}")  

tic = TicUSB()  

tic.set_step_mode(0)                  # Full step  
tic.set_current_limit(46)             # ~1.5A  
tic.set_max_speed(100000000)              # Reasonable speed  
tic.set_starting_speed(00)           # Nonzero  
tic.set_max_acceleration(500000)       # Reasonable acceleration  
tic.set_max_deceleration(500000)  
tic.set_decay_mode(0)                 # Automatic decay, usually best  

print_registers(tic)  

try:  
    tic.halt_and_set_position(0)  
    tic.energize()  
    tic.exit_safe_start()  

    positions = [-10000]
    for position in positions:  
        print("Moving to position:", position)  
        tic.set_target_position(position)  
        while abs(tic.get_current_position() - position) > 1:  
            tic.reset_command_timeout()  # keep alive during move  
            sleep(0.3)  
        print(f"Arrived: {tic.get_current_position()}")  
        sleep(0.1)  # let it settle  
except KeyboardInterrupt:  
    print("\nKeyboard interrupt detected. Stopping motor safely...")  
except Exception as e:  
    print(f"\nError occurred: {e}")  
finally:  
    # Use get_errors_occurred() if your library has it. Otherwise, use get_error_status().  
    if hasattr(tic, "get_errors_occurred"):  
        print("Get errors:", tic.get_errors_occurred())  
    print("Error status:", tic.get_error_status())  
    print("\nShutting down motor...")  
    tic.deenergize()  
    tic.enter_safe_start()  