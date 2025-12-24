import RPi.GPIO as GPIO
import time
import sys
import os


class PumpTester:
    def __init__(self, relay_pin=27, safety_timeout=10000):
        self.relay_pin = relay_pin
        self.safety_timeout = safety_timeout
        self.setup_gpio()

    def setup_gpio(self):
        """Setup GPIO for relay"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relay_pin, GPIO.OUT)
        GPIO.output(self.relay_pin, GPIO.HIGH)
        print(" GPIO initialized")

    def test_relay_click(self):
        """Test relay clicking sound"""
        print("\n RELAY CLICK TEST")

        for i in range(5):
            print(f"\nCycle {i + 1}:")
            print("  Relay ON...", end="")
            GPIO.output(self.relay_pin, GPIO.LOW)
            print("(listen for click)")
            time.sleep(0.5)

            print("  Relay OFF...", end="")
            GPIO.output(self.relay_pin, GPIO.HIGH)
            print("(listen for click)")
            time.sleep(0.5)

        print("\n Relay test complete!")

    def test_pump_short(self):
        """Test pump with short burst"""
        print("\n SHORT PUMP TEST (1 second)")
        print("-" * 40)
        print(" IMPORTANT:")
        print("1. Pump must be in water")
        print("2. Battery switch must be ON")
        print("3. Ready for water to flow")

        response = input("\nReady? (yes/no): ").strip().lower()

        if response != 'yes':
            print("Test cancelled")
            return False

        print("\n Starting 1-second pump test...")
        GPIO.output(self.relay_pin, GPIO.LOW)
        print(" Pump ON - Water should flow")

        # Run for 1 second
        start_time = time.time()
        while time.time() - start_time < 1:
            elapsed = time.time() - start_time
            print(f"  Running: {elapsed:.1f}s / 1.0s", end='\r')
            time.sleep(0.1)

        GPIO.output(self.relay_pin, GPIO.HIGH)
        print("\nPump OFF - Water should stop")

        # Verify
        success = input("\nDid water flow? (yes/no): ").strip().lower()
        return success == 'yes'

    def test_pump_duration(self, duration_ms):
        """Test pump for specific duration"""
        print(f"\n  PUMP DURATION TEST ({duration_ms}ms)")
        print("-" * 40)

        print(f"Testing pump for {duration_ms / 1000:.1f} seconds")
        print("Listen for pump sound and watch water flow")

        GPIO.output(self.relay_pin, GPIO.LOW)
        start_time = time.time()

        try:
            while time.time() - start_time < (duration_ms / 1000):
                elapsed = (time.time() - start_time) * 1000
                remaining = duration_ms - elapsed
                print(f"  Pump ON: {elapsed:.0f}ms / {duration_ms}ms | Remaining: {remaining:.0f}ms", end='\r')
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n  Test interrupted!")
        finally:
            GPIO.output(self.relay_pin, GPIO.HIGH)

        print(f"\n Pump ran for {duration_ms}ms")
        return True

    def emergency_stop(self):
        """Emergency stop function"""
        print("\n EMERGENCY STOP!")
        GPIO.output(self.relay_pin, GPIO.HIGH)
        print(" Pump stopped")

    def cleanup(self):
        """Cleanup GPIO"""
        GPIO.cleanup()
        print("GPIO cleaned up")


def main_menu():
    """Interactive test menu"""
    tester = PumpTester()

    try:
        while True:
            print("\n" + "=" * 60)
            print("            PUMP TESTING MENU")
            print("=" * 60)
            print("\nBEFORE STARTING:")
            print("Raspberry Pi powered ON")
            print("Relay connected to GPIO 27")
            print("Pump in water (for water tests)")
            print("Battery switch ON (for water tests)")

            print("\nSelect test:")
            print("1.  Test relay clicking (no water needed)")
            print("2.  Test pump - 1 second burst")
            print("3. ️  Test pump - 3 seconds (normal watering)")
            print("4.  Test pump - 10 seconds (max safety)")
            print("5.  Run all tests in sequence")
            print("6.  Emergency stop (if pump stuck)")
            print("7.  Exit")

            choice = input("\nEnter choice (1-7): ").strip()

            if choice == "1":
                tester.test_relay_click()
            elif choice == "2":
                tester.test_pump_short()
            elif choice == "3":
                tester.test_pump_duration(3000)
            elif choice == "4":
                tester.test_pump_duration(10000)
            elif choice == "5":
                print("\n🔧 RUNNING ALL TESTS...")
                tester.test_relay_click()
                time.sleep(1)
                if tester.test_pump_short():
                    time.sleep(2)
                    tester.test_pump_duration(3000)
                    time.sleep(2)
                    tester.test_pump_duration(10000)
                print("\n🎉 ALL TESTS COMPLETE!")
            elif choice == "6":
                tester.emergency_stop()
            elif choice == "7":
                print("\nExiting...")
                break
            else:
                print(" Invalid choice")

            input("\nPress Enter to continue...")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n Error: {e}")
    finally:
        tester.cleanup()


if __name__ == "__main__":
    # Check if running with sudo
    if os.geteuid() != 0:
        print("  This script requires sudo for GPIO access.")
        print("   Run with: sudo python3 test_pump_final.py")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("      SMART PLANT IRRIGATION - PUMP TEST")
    print("=" * 60)

    main_menu()