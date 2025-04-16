from ticlib import TicUSB
import threading
import time
import queue

class TicController:
    def __init__(self):
        self.tic = TicUSB()
        self.position_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.movement_thread = None
        self.sensor_thread = None
        self.current_position = 0
        self.target_position = 0
        self.position_reached_event = threading.Event()
        self.lock = threading.Lock()
        self.sensor_data = {}
        
    def setup(self):
        """Initialize the Tic with optimized parameters"""
        print("Setting up motor controller...")
        
        self.tic.set_step_mode(0)               # Full step for max torque
        self.tic.set_current_limit(46)          # ~1.5A
        self.tic.set_max_speed(100000000)       # Higher speed
        self.tic.set_starting_speed(0000)       # Non-zero starting speed
        self.tic.set_max_acceleration(500000)  # Higher acceleration   from 1000000
        self.tic.set_max_deceleration(500000)  # Higher deceleration
        self.tic.set_decay_mode(0)              
        
        #self.tic.halt_and_set_position(0)
      
        
        # Initialize position tracking
        with self.lock:
            self.current_position = self.tic.get_current_position()
            self.target_position = self.current_position
    
    def motor_position_monitor(self):
        """Thread to monitor motor position and process movement commands"""
        print("Motor position monitor started")
        
        while not self.stop_event.is_set():
            try:
                # Check if there's a new position in the queue
                try:
                    new_position = self.position_queue.get(block=False)
                    print(f"New target position: {new_position}")
                    
                    # Reset the position reached event
                    self.position_reached_event.clear()
                    
                    # Set the new target position
                    with self.lock:
                        self.target_position = new_position
                    
                    # Send the command to the motor
                    self.tic.set_target_position(new_position)
                    self.tic.exit_safe_start()
                    
                    # Mark the queue task as done
                    self.position_queue.task_done()

                    #Keep commands alive
                    self.tic.reset_command_timeout()   # ADDED: prevent command timeout  

                except queue.Empty:
                    pass
                
                # Update current position
                with self.lock:
                    self.current_position = self.tic.get_current_position()
                
                # Check if position has been reached
                if not self.position_reached_event.is_set() and self.current_position == self.target_position:
                    print(f"Position reached: {self.current_position}")
                    self.position_reached_event.set()
                
                # Periodically exit safe start to keep controller responsive
                self.tic.exit_safe_start()
                
            except Exception as e:
                print(f"Motor monitor error: {e}")
                
            # Check position 10 times per second
            time.sleep(0.1)
        
        print("Motor position monitor stopped")
    
    def sensor_monitor(self):
        """Thread to read sensor data"""
        print("Sensor monitor started")
        
        while not self.stop_event.is_set():
            try:
                # Read sensor data - replace this with your actual sensor code
                # For demonstration, we'll just record the motor position and timestamp
                timestamp = time.time()
                position = self.tic.get_current_position()
                
                # You can add any other sensor readings here
                # sensor1_value = read_sensor1()
                # sensor2_value = read_sensor2()
                
                # Store the sensor data with thread-safe access
                with self.lock:
                    self.sensor_data[timestamp] = {
                        'position': position,
                        # 'sensor1': sensor1_value,
                        # 'sensor2': sensor2_value,
                    }
                
                # Print current data (optional)
                if len(self.sensor_data) % 10 == 0:  # Print every 10th reading
                    print(f"Recorded data point {len(self.sensor_data)}: Position = {position}")
                    
            except Exception as e:
                print(f"Sensor monitor error: {e}")
                
            # Read sensors 5 times per second - adjust as needed
            time.sleep(0.2)
        
        print("Sensor monitor stopped")
    
    def start(self):
        """Start the controller threads"""
        self.setup()
        self.stop_event.clear()
        self.position_reached_event.clear()
        
        # Start motor position monitor thread
        self.movement_thread = threading.Thread(target=self.motor_position_monitor)
        self.movement_thread.daemon = True
        self.movement_thread.start()
        
        # Start sensor monitor thread
        self.sensor_thread = threading.Thread(target=self.sensor_monitor)
        self.sensor_thread.daemon = True
        self.sensor_thread.start()
        
        print("Controller started")
        self.tic.energize()
        self.tic.exit_safe_start()
    
    def stop(self):
        """Stop the controller threads"""
        self.stop_event.set()
        
        # Wait for threads to finish
        if self.movement_thread and self.movement_thread.is_alive():
            self.movement_thread.join(timeout=5.0)
        if self.sensor_thread and self.sensor_thread.is_alive():
            self.sensor_thread.join(timeout=5.0)
        
        # De-energize the motor
        self.tic.deenergize()
        self.tic.enter_safe_start()
            
        print("Controller stopped")
    
    def move_to(self, position):
        """Queue a new position to move to"""
        self.position_queue.put(position)
    
    def wait_for_position_reached(self, timeout=None):
        """Wait until the current target position is reached"""
        return self.position_reached_event.wait(timeout)
    
    def get_sensor_data(self):
        """Get a copy of the sensor data"""
        with self.lock:
            return self.sensor_data.copy()
    
    def get_current_position(self):
        """Get the current position"""
        with self.lock:
            return self.current_position
        
    def reset_position(self):  
        """Reset the current position to zero"""  
        print("Resetting position to zero...")  
        
        # Clear any pending movements  
        while not self.position_queue.empty():  
            try:  
                self.position_queue.get_nowait()  
                self.position_queue.task_done()  
            except queue.Empty:  
                break  
                
        # Halt and set position to zero in the controller  
        self.tic.halt_and_set_position(0)  
        
        # Update internal tracking  
        with self.lock:  
            self.current_position = 0  
            self.target_position = 0  
        
        # Set the position reached event since we're at the target  
        self.position_reached_event.set()  
        
        print("Position reset complete")  


# Example usage
def run_test():
    controller = TicController()
    controller.start()
    
    
    try:
        # Move to a series of positions
        positions = [-1500,0,1000,0]
         # Reset the position to zero  
        print("\nResetting position to zero...")  
        controller.reset_position()  
        time.sleep(1)  # Brief pause  
        
        for position in positions:
            print(f"\nMoving to position {position}...")
            controller.move_to(position)
            
            # Wait until position is reached, with timeout
            if controller.wait_for_position_reached(timeout=30):
                print(f"Successfully reached position {position}")
            else:
                print(f"Timeout waiting for position {position}")
            
            # You can access sensor data at any time
            sensor_data = controller.get_sensor_data()
            print(f"Collected {len(sensor_data)} sensor readings so far")
            
            # Wait a bit between movements
            print("Waiting before next movement...")
            time.sleep(2)
        
        # Show final position
        print(f"\nFinal position: {controller.get_current_position()}")
        
        # Example of analyzing sensor data
        sensor_data = controller.get_sensor_data()
        timestamps = sorted(sensor_data.keys())
        if timestamps:
            print("\nSensor data summary:")
            print(f"  First reading: {sensor_data[timestamps[0]]}")
            print(f"  Last reading: {sensor_data[timestamps[-1]]}")
            print(f"  Total readings: {len(timestamps)}")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        controller.stop()


if __name__ == "__main__":
    print("\n=== MOTOR AND SENSOR TEST ===\n")
    run_test()
    print("\n=== TEST COMPLETED ===")
    