from migen import *
from litex.build.lattice import LatticeECP5Platform
from litex.build.generic_platform import Pins, IOStandard, Misc, Subsignal
from litex.build.lattice.programmer import EcpDapProgrammer
from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.builder import Builder
from litex.soc.cores.cpu.vexriscv import VexRiscv
from litedram.modules import MT41K256M16
from litedram.phy.ecp5ddrphy import ECP5DDRPHY
from litedram.core.controller import LiteDRAMController
from litex.soc.cores.clock import ECP5PLL

# Blinking LED Module
class BlinkingLED(Module):
    def __init__(self, platform):
        self.led = platform.request("user_led_n")
        self.counter = Signal(24)

        # Create a blinking LED pattern
        self.sync += self.counter.eq(self.counter + 1)
        self.sync += self.led.eq(self.counter[23])  # Blink at ~1Hz

# IceSugar Platform Definition
class IceSugarPlatform(LatticeECP5Platform):
    default_clk_name = "clk25"
    default_clk_period = 1e9 / 25e6  # 25 MHz clock period

    def __init__(self):
        device = "LFE5U-25F-6BG256C"

        # Define I/O pins
        io = [
            ("user_led_n", 0, Pins("B11"), IOStandard("LVCMOS33")),  # Red LED
            ("clk25", 0, Pins("P6"), IOStandard("LVCMOS33")),        # Clock pin
            ("serial", 0,
                Subsignal("tx", Pins("B9")),
                Subsignal("rx", Pins("A9")),
                IOStandard("LVCMOS33")
            ),
            # SDRAM Definition
            ("sdram", 0,
             Subsignal("clk_p", Pins("R15")),
             Subsignal("a", Pins("H15 B13 B12 J16 J15 R12 K16 R13 T13 K15 A13 R14 T14")),
             Subsignal("dq", Pins("F16 E15 F15 D14 E16 C15 D16 B15 R16 P16 P15 N16 N14 M16 M15 L15")),
             Subsignal("dqs_p", Pins("G14")),  # Differential strobe positive
             Subsignal("dqs_n", Pins("F14")),  # Differential strobe negative
             Subsignal("we_n", Pins("A15")),
             Subsignal("ras_n", Pins("B16")),
             Subsignal("cas_n", Pins("G16")),
             Subsignal("cs_n", Pins("A14")),
             Subsignal("cke", Pins("L16")),
             Subsignal("ba", Pins("G15 B14")),
             Subsignal("dm", Pins("C16 T15")),
             IOStandard("LVCMOS33"),
             Misc("SLEWRATE=FAST")
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
    def __init__(self, platform, clk_freq=50e6):
        # Initialize SoCCore
        SoCCore.__init__(self, platform, clk_freq,
                         cpu_type="vexriscv",
                         csr_data_width=32,
                         integrated_rom_size=0x8000,
                         integrated_sram_size=0x4000,
                         uart_baudrate=115200)

        # Define clock domains
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys2x = ClockDomain()
        self.clock_domains.cd_init = ClockDomain()  # Added init clock domain

        # PLL Configuration
        self.submodules.pll = pll = ECP5PLL()
        pll.register_clkin(platform.request("clk25"), 25e6)
        pll.create_clkout(self.cd_sys, clk_freq)       # Main system clock
        pll.create_clkout(self.cd_sys2x, 2 * clk_freq)  # 2x system clock
        pll.create_clkout(self.cd_init, 25e6)  # Set the init clock domain to 25MHz

        # DDR PHY Configuration and SDRAM Controller
        try:
            self.submodules.ddrphy = ECP5DDRPHY(platform.request("sdram"))
            self.add_csr("ddrphy")

            sdram_module = MT41K256M16(clk_freq, "1:2")
            self.submodules.sdram_controller = LiteDRAMController(
                sdram_module, self.ddrphy, clk_freq=clk_freq)
            self.add_csr("sdram_controller")
            self.add_constant("MEMTEST_BUS_SIZE", 16)
        except Exception as e:
            print(f"Error initializing SDRAM module: {e}")

        # Add blinking LED module
        self.submodules.blinking_led = BlinkingLED(platform)
        self.add_csr("blinking_led")

# Main Entry Point
if __name__ == "__main__":
    platform = IceSugarPlatform()
    soc = MySoC(platform)
    builder = Builder(soc, csr_csv="csr.csv")
    builder.build()

