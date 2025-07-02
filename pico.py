from migen import *
from litex.build.lattice import LatticeECP5Platform
from litex.build.generic_platform import Pins, IOStandard, Misc, Subsignal
from litex.build.lattice.programmer import EcpDapProgrammer
from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.builder import Builder
from litex.soc.cores.cpu.picorv32 import PicoRV32  

# Blinking LED Module
class BlinkingLED(Module):
    def __init__(self, platform, led_pin):
        self.led_pin = platform.request(led_pin)  
        self.counter = Signal(24)
        self.blink_count = Signal(4)
        self.blink_active = Signal(reset=1)
        self.led_state = Signal()
        self.sync += self.counter.eq(self.counter + 1)
        self.sync += self.led_pin.eq(self.counter[23])
        self.sync += If(self.blink_count == 10,
           self.blink_active.eq(0),
           self.led_pin.eq(0)
        )

# IceSugar Platform Definition
class IceSugarPlatform(LatticeECP5Platform):
    default_clk_name = "clk25"
    default_clk_period = 1e9 / 25e6  # 25 MHz clock period

    def __init__(self):
        device = "LFE5U-25F-6BG256C"

        # Define I/O pins
        io = [
            ("user_led_n", 0, Pins("B11"), IOStandard("LVCMOS33")),  # Red LED
            ("user_led_n", 1, Pins("A11"), IOStandard("LVCMOS33")),  # Green LED
            ("user_led_n", 2, Pins("A12"), IOStandard("LVCMOS33")),  # Blue LED
            ("clk25", 0, Pins("P6"), IOStandard("LVCMOS33")),
            ("cpu_reset_n", 0, Pins("L14"), IOStandard("LVCMOS33"), Misc("PULLMODE=UP")),
            ("serial", 0, 
                Subsignal("tx", Pins("B9")),
                Subsignal("rx", Pins("A9")),
                IOStandard("LVCMOS33")
            ),
        ]

        connectors = [
            ("pmode", "N3 M2 L2 G2 P1 N1 M1 K1"),
            ("pmodf", "T6 R5 R4 R3 P7 R6 T4 T3"),
        ]

        # Initialize platform with device and I/O
        LatticeECP5Platform.__init__(self, device, io, connectors=connectors, toolchain="trellis")

    def create_programmer(self):
        return EcpDapProgrammer()

    def do_finalize(self, fragment):
        LatticeECP5Platform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("clk25", loose=True), self.default_clk_period)

# SoC Definition with PicoRV32 Core
class MySoC(SoCCore):
    def __init__(self, platform):
        SoCCore.__init__(self, platform,
                         cpu_type="picorv32",
                         clk_freq=25e6,
                         integrated_rom_size=0x10000,
                         integrated_sram_size=0x10000,
                         uart=None)
        self.submodules.blinking_led = BlinkingLED(platform, "user_led_n")

# Main Entry Point
if __name__ == "__main__":
    platform = IceSugarPlatform()
    soc = MySoC(platform)
    builder = Builder(soc)
    builder.build()
