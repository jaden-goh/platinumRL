# Platinum RL Starter — V0.1

An **experimental** minimal Libretro frontend, a deterministic movement policy, and a Pygame viewer. This is not yet a reinforcement learning agent. The native DeSmuME core and the game ROM are **not bundled**. The starter has been syntax-checked but **not runtime-tested against a DeSmuME DLL or a Platinum ROM**. Core-specific compatibility issues may need debugging.

## Bash / WSL setup

1. Install Python 3.11, Git, and the native libraries needed by Pygame. On Ubuntu/WSL:
   ```bash
   sudo apt update
   sudo apt install -y python3.11 python3.11-venv python3-pip git libsdl2-2.0-0
   ```
2. In Bash, inside this folder:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
3. Install **RetroArch for Linux** in the same environment you will run Python from. In RetroArch use **Online Updater → Core Downloader → Nintendo - DS (DeSmuME)**. Find the downloaded `desmume_libretro.so` in RetroArch's `cores` directory and **copy** it into this project's `cores/` directory. Alternatively pass its absolute path using `--core`. Use the standard DeSmuME core, not DeSmuME 2015 for this initial test. Core and Python must both be 64-bit.

   In WSL, use WSLg or another X server so the Pygame window can open.
4. Place your own legally obtained compatible Pokémon Platinum ROM at `roms/platinum.nds`. The ROM is not included. If the core requires firmware for your configuration, place your own legally obtained BIOS/firmware files in `system/`; the default DeSmuME setup typically does not require external BIOS.
5. Run:
   ```bash
   python main.py
   ```
   Or choose explicit paths: `python main.py --core "/path/to/desmume_libretro.so" --rom "/path/to/Platinum.nds"`.
6. Use the in-game buttons normally to complete the opening sequence **before expecting movement to work**. Start in **manual mode**. Use arrow keys and Z/X/Enter to complete the introduction until your character can walk around. Press F5 to save a state, then M to enable the automatic square policy. Next time you can launch with `--state saves/quick.state`.

## Controls

- Arrow keys: D-pad; Z: A; X: B; Enter: Start; Backspace: Select; A: X; S: Y (in manual mode)
- M: toggle between manual gameplay and automatic square policy (starts in manual mode)
- ESC: quit
- F5: write `saves/quick.state` using Libretro serialization
- F8: restore `saves/quick.state`
- Automated policy: RIGHT → DOWN → LEFT → UP, repeating. This draws a square only in an unobstructed overworld area; walls, NPCs, menus, and scripted events can prevent movement.

## File ownership and edit points

| File | Layer | What it does | Edit when... |
|---|---|---|---|
| `main.py` | Application | Runs main loop and wires everything together | Add agents, change execution settings, pause/record |
| `emulator/libretro.py` | Native adapter | Loads the Libretro core, registers callbacks, steps frames, captures framebuffer, serializes states | Add touch input, memory reading, core settings, debugging |
| `agents/circle.py` | Policy | Picks a direction each frame | Replace square with exploration or RL policy |
| `viewer/display.py` | Presentation | Renders the emulator-provided framebuffer in a window | Add multi-agent grid, overlays, or dashboard |
| `requirements.txt` | Dependencies | Python packages | Add Gymnasium, SB3, OpenCV later |
| `cores/` | Native binary | DeSmuME Libretro core, such as `.so` on Linux/WSL or `.dll` on Windows (user-provided) | Switch emulator backend |
| `roms/` | Game content | Your `.nds` ROM (user-provided) | Change game/region |
| `system/` | Firmware | Optional legally obtained firmware | Core needs external firmware |
| `saves/` | Persistent data | Quick savestates | Reset episodes |

## Limitations

- Manual keyboard gameplay is supported; touchscreen input is not yet supported.
- No game memory reader, no Gymnasium environment, no RL training.
- No support for hardware-rendered Libretro cores; this code expects software video callbacks.
- No full Libretro environment command support; some cores may request unsupported callbacks/options.
- The Pygame window is capped to 60 Hz by default, so it is not optimized for accelerated RL training.
- No sound output.
- This is a single-core, single-instance prototype; run separate worker processes for future parallel environments.
- Libretro cores are native code. If the core crashes, the Python process can terminate; there is no sandbox isolation.

## First acceptance test

- Core loads without an error.
- Both screens display correctly.
- Automated button sequence is issued without desktop keyboard automation.
- A walkable save state shows repeated square movement.
- F5/F8 round-trips state within this app.

If the game launches but does not move, it may still be at a title screen, dialogue, or against an obstacle. Movement isn't guaranteed just by sending D-pad commands.
