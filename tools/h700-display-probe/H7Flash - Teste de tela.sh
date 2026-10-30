#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
PROBEDIR="$HERE/H7Flash-teste-tela"
if [ ! -f "$PROBEDIR/h700-display-probe" ]; then
  echo "Pasta H7Flash-teste-tela ausente" > "$HERE/h7flash_tela_erro.txt"
  exit 1
fi
exec > "$PROBEDIR/resultado.txt" 2>&1
echo "=== H7Flash SDL2 display probe ==="
date
uname -a
XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}
for pm in /opt/system/Tools/PortMaster /opt/tools/PortMaster "$XDG_DATA_HOME/PortMaster" /mnt/mmc/MUOS/PortMaster /roms/ports/PortMaster; do
  if [ -f "$pm/control.txt" ]; then
    controlfolder="$pm"
    source "$pm/control.txt"
    [ ! -f "$pm/mod_${CFW_NAME}.txt" ] || source "$pm/mod_${CFW_NAME}.txt"
    command -v get_controls >/dev/null 2>&1 && get_controls
    break
  fi
done
export SDL_GAMECONTROLLERCONFIG="${sdl_controllerconfig:-${SDL_GAMECONTROLLERCONFIG:-}}"
# Let the firmware SDL choose its native backend; do not force RK3326 DRM.
unset SDL_VIDEODRIVER SDL_VIDEO_DRIVER SDL_RENDER_DRIVER EGL_PLATFORM DISPLAY WAYLAND_DISPLAY
echo "SDL libraries:"
ls -l /usr/lib/libSDL2* /usr/lib64/libSDL2* /usr/lib/aarch64-linux-gnu/libSDL2* 2>/dev/null
echo "Display devices:"
ls -l /dev/dri /dev/fb0 /dev/mali0 2>/dev/null
cleanup() {
  command -v pm_finish >/dev/null 2>&1 && pm_finish
  return 0
}
trap cleanup EXIT
chmod +x "$PROBEDIR/h700-display-probe"
if command -v timeout >/dev/null 2>&1; then
  timeout -k 3 25 "$PROBEDIR/h700-display-probe"
  result=$?
else
  echo "FAIL timeout command unavailable; probe not started"
  result=127
fi
echo "probe_exit=$result"
exit "$result"
