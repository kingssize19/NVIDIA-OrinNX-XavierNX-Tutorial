#!/usr/bin/env python3
import os, re, subprocess

PINMUX_PATH = "/sys/kernel/debug/pinctrl/2430000.pinmux"
GPIO_BASE = {
    "tegra-gpio": 0x2200000,
    "tegra-gpio-aon": 0xC2F0000,
}

GPIO_BANK_SIZE = 0x1000

def read_file(path):
    try:
        return open(path).read().strip()
    except:
        return None

def parse_pinmux_functions():
    funcs = {}
    txt = read_file(f"{PINMUX_PATH}/pinmux-functions")
    current = None
    for line in txt.splitlines():
        if line.startswith("function:"):
            parts = line.split()
            fname = parts[1].replace(",", "")
            current = fname
            funcs[current] = []
            continue
        if "groups =" in line:
            groups = re.findall(r'\b[\w\d_]+\b', line)
            for g in groups:
                if g not in ("function", "groups"):
                    funcs[current].append(g)
    return funcs

def parse_pinmux_pins():
    pins = {}
    txt = read_file(f"{PINMUX_PATH}/pinmux-pins")
    for line in txt.splitlines():
        m = re.match(r"pin (\d+) \((.*?)\): \(MUX (.*?)\) (.*)", line)
        if m:
            pin = int(m.group(1))
            name = m.group(2)
            mux_owner = m.group(3)
            gpio_owner = m.group(4).strip()
            pins[pin] = {
                "name": name,
                "mux_owner": mux_owner,
                "gpio_owner": gpio_owner,
            }
    return pins

def resolve_gpio_registers(gpio_num, controller):
    base = GPIO_BASE.get(controller)
    if base is None:
        return None

    bank = gpio_num // 8
    bit = gpio_num % 8

    reg_base = base + GPIO_BANK_SIZE * bank

    return {
        "bank": bank,
        "bit": bit,
        "CNF": hex(reg_base + 0x0C0),
        "OE": hex(reg_base + 0x0D0),
        "OUT": hex(reg_base + 0x0E0),
        "IN": hex(reg_base + 0x100),
    }

def read_gpio_value(controller, reg):
    return None  # DO NOT READ RAW REGISTERS (PROTECTED)

def detect_pin_function(pinname, funcs):
    for func, groups in funcs.items():
        if pinname in groups:
            return func
    return "UNASSIGNED"

def main():
    print("\n=== XAVIER NX – FULL PIN ANALYSIS ===\n")

    pins = parse_pinmux_pins()
    funcs = parse_pinmux_functions()

    for pin, info in sorted(pins.items()):
        name = info["name"]
        mux_owner = info["mux_owner"]
        gpio_owner = info["gpio_owner"]

        print(f"\nPIN {pin}: {name}")
        print(f"  MUX Owner : {mux_owner}")
        print(f"  GPIO Owner: {gpio_owner}")

        # 1) FUNCTION (SFIO / UART / I2C / SPI / SDMMC ...)
        fn = detect_pin_function(name, funcs)
        print(f"  Function  : {fn}")

        # 2) GPIO MODE?
        if "tegra-gpio" in gpio_owner:
            gpio_num = int(re.findall(r'\d+', gpio_owner)[0])
            controller = "tegra-gpio"
            if "aon" in gpio_owner:
                controller = "tegra-gpio-aon"

            print(f"  GPIO Num  : {gpio_num} ({controller})")

            regs = resolve_gpio_registers(gpio_num, controller)
            if regs:
                print(f"  Bank/Bit  : bank={regs['bank']}  bit={regs['bit']}")
                print(f"  CNF reg   : {regs['CNF']}")
                print(f"  OE  reg   : {regs['OE']}")
                print(f"  OUT reg   : {regs['OUT']}")
                print(f"  IN  reg   : {regs['IN']}")

        # 3) DESCRIPTIONS (Auto explain)
        if "usb_vbus" in name:
            print("  Info      : USB power switch enable")
        elif "dp_aux" in name:
            print("  Info      : DisplayPort AUX Hotplug detect")
        elif name.startswith("soc_gpio"):
            print("  Info      : General purpose SOC GPIO")
        elif name.startswith("cam"):
            print("  Info      : Camera I2C or control pin")
        elif "i2c" in fn:
            print("  Info      : I2C bus line")
        elif "uart" in fn:
            print("  Info      : UART communication")
        elif "spi" in fn:
            print("  Info      : SPI bus pin")
        elif "sdmmc" in fn:
            print("  Info      : SD/MMC controller pin")

if __name__ == "__main__":
    main()

