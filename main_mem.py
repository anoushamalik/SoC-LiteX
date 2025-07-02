from migen import *
from litex.build.lattice import LatticeECP5Platform
from litex.build.generic_platform import Pins, IOStandard, Misc, Subsignal
from litex.build.lattice.programmer import EcpDapProgrammer
from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.builder import Builder
from litex.soc.cores.cpu.vexriscv import VexRiscv
from litex.soc.integration.soc import SoCRegion
from litedram import modules as litedram_modules
from litedram.phy.model import SDRAMPHYModel
from litex.soc.integration.soc_core import *
from litex.tools.litex_sim import sdram_module_nphases, get_sdram_phy_settings
from litex.soc.interconnect.csr import *

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
        If(self.blink_count == 10,
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
            ("user_led_n", 0, Pins("B11"), IOStandard("LVCMOS33")),  # Red
            ("clk25", 0, Pins("P6"), IOStandard("LVCMOS33")),  # Clock pin
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

        LatticeECP5Platform.__init__(self, device, io, connectors=connectors, toolchain="trellis")

    def create_programmer(self):
        return EcpDapProgrammer()
    
    def do_finalize(self, fragment):
        LatticeECP5Platform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("clk25", loose=True), self.default_clk_period)


# SoC Definition with VexRiscv Core
class MySoC(SoCCore):
    def __init__(self, platform):
        # Initialize SoC Core with VexRiscv CPU, UART, and memory
        SoCCore.__init__(self, platform,
                         cpu_type="vexriscv", 
                         clk_freq=25e6,
                         integrated_rom_size=0x8000,
                         integrated_sram_size=0x4000,
                         #integrated_main_ram_size=0x1000000,
                         uart_baudrate=115200) 

        # Add main memory region to the SoC
        self.bus.add_region(
            "main_ram", 
            SoCRegion(
                origin=0x40000000,  # Address for main RAM
                size=0x1000000,    # 16 MB
                cached=True
            )
        )

        # Adding blinking LED module
        self.submodules.blinking_led = BlinkingLED(platform, "user_led_n")


# Main Entry Point
if __name__ == "__main__":
    platform = IceSugarPlatform()
    soc = MySoC(platform)
    builder = Builder(soc)
    builder.build()
