#!/usr/bin/env python3
# H7Flash - tela de menu (estilo emulador) que lista os .swf de H7Flash/games.
# Chamado pelo H7Flash.sh. Escreve o caminho do jogo escolhido em $FLASH_CHOICE_FILE.
# Codigos de saida: 0 = jogo escolhido, 1 = usuario saiu, 3 = SDL2 indisponivel / erro.
#
# Controles: CIMA/BAIXO escolhe, ESQUERDA/DIREITA (ou L1/R1) pula de pagina,
#            A joga, START abre opcoes, B ou SELECT/MENU sai.
# Se A e B estiverem trocados no seu aparelho, crie H7Flash/menu.cfg com:  swap_ab=1

import os, sys, glob, zlib, ctypes, time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "menu_log.txt")
CHOICE_FILE = os.environ.get("FLASH_CHOICE_FILE") or os.path.join(HERE, "menu_choice.txt")
LAST_FILE = os.path.join(HERE, "menu_last.txt")
GAMES = os.environ["H7FLASH_GAMES"]


def log(*a):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(" ".join(str(x) for x in a) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------- SDL2 import
cf = os.environ.get("controlfolder") or os.environ.get("CONTROLFOLDER") or ""
for p in (cf + "/exlibs", cf + "/pylibs", "/mnt/mmc/MUOS/PortMaster/exlibs", "/mnt/mmc/MUOS/PortMaster/pylibs",
          "/mnt/sdcard/MUOS/PortMaster/exlibs", "/opt/muos/extra/python", "/opt/python/lib/python3/site-packages"):
    if p and os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
for d in ("/usr/lib64", "/usr/lib", "/usr/lib/aarch64-linux-gnu", "/opt/muos/extra/lib"):
    if os.path.exists(d + "/libSDL2.so") or os.path.exists(d + "/libSDL2-2.0.so.0"):
        os.environ.setdefault("PYSDL2_DLL_PATH", d)
        break

try:
    import sdl2
    import game_options
except Exception as e:  # noqa
    log("ERRO: nao consegui importar sdl2 (pySDL2):", repr(e))
    log("sys.path =", sys.path)
    log("PYSDL2_DLL_PATH =", os.environ.get("PYSDL2_DLL_PATH"))
    sys.exit(3)


# ---------------------------------------------------------------- jogos
def pretty(name):
    base = os.path.splitext(name)[0]
    s = " ".join(base.replace("_", " ").replace("-", " ").split())
    return s or base


def list_games():
    files = set()
    for pat in ("*.swf", "*.SWF", "*.Swf"):
        files.update(glob.glob(os.path.join(GAMES, pat)))
    items = [(pretty(os.path.basename(f)), f) for f in files if os.path.isfile(f)]
    items.sort(key=lambda t: t[0].lower())
    return items


def read_cfg():
    cfg = {}
    try:
        for line in open(os.path.join(HERE, "menu.cfg"), encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip().lower()] = v.strip()
    except OSError:
        pass
    return cfg


# ---------------------------------------------------------------- fonte bitmap
class Font:
    def __init__(self, path):
        raw = open(path, "rb").read()
        assert raw[:4] == b"FNT1"
        n = raw[4]
        dims = [(raw[5 + 2 * i], raw[6 + 2 * i]) for i in range(n)]
        data = zlib.decompress(raw[5 + 2 * n:])
        self.sizes = []
        off = 0
        for cw, ch in dims:
            cell = cw * ch
            glyphs = [data[off + i * cell: off + (i + 1) * cell] for i in range(224)]
            off += 224 * cell
            self.sizes.append((cw, ch, glyphs))
        self.cache = {}

    def metrics(self, size):
        return self.sizes[size][0], self.sizes[size][1]

    def width(self, size, text):
        return self.sizes[size][0] * len(text)

    def glyph(self, size, ch, color):
        key = (size, ch, color)
        s = self.cache.get(key)
        if s is not None:
            return s
        cw, chh, glyphs = self.sizes[size]
        code = ord(ch)
        if code < 32 or code > 255:
            code = 63  # '?'
        a = glyphs[code - 32]
        buf = bytearray(cw * chh * 4)
        buf[0::4] = bytes([color[2]]) * (cw * chh)   # B
        buf[1::4] = bytes([color[1]]) * (cw * chh)   # G
        buf[2::4] = bytes([color[0]]) * (cw * chh)   # R
        buf[3::4] = a                                # A
        keep = (ctypes.c_char * len(buf)).from_buffer(buf)
        surf = sdl2.SDL_CreateRGBSurfaceFrom(keep, cw, chh, 32, cw * 4,
                                             0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
        sdl2.SDL_SetSurfaceBlendMode(surf, sdl2.SDL_BLENDMODE_BLEND)
        s = (surf, buf, keep)  # mantem o buffer vivo
        self.cache[key] = s
        return s

    def draw(self, dst, size, x, y, text, color):
        cw, chh = self.metrics(size)
        for i, ch in enumerate(text):
            if ch == " ":
                continue
            surf = self.glyph(size, ch, color)[0]
            r = sdl2.SDL_Rect(x + i * cw, y, cw, chh)
            sdl2.SDL_BlitSurface(surf, None, dst, r)


def fit(text, size, font, maxw):
    cw = font.metrics(size)[0]
    maxc = max(1, maxw // cw)
    if len(text) <= maxc:
        return text
    return text[:maxc - 3] + "..."


# ---------------------------------------------------------------- cores
BG = (16, 20, 38)
BAR = (28, 34, 62)
ACC = (232, 87, 58)
TXT = (214, 220, 240)
DIM = (130, 140, 175)
WHITE = (255, 255, 255)


def main():
    games = list_games()
    cfg = read_cfg()
    swap = cfg.get("swap_ab", "0") in ("1", "true", "yes")
    log("menu iniciado;", len(games), "jogo(s); swap_ab =", swap)

    last = ""
    try:
        last = open(LAST_FILE, encoding="utf-8").read().strip()
    except OSError:
        pass
    sel = 0
    for i, (_, p) in enumerate(games):
        if os.path.basename(p) == last:
            sel = i
            break

    try:
        font = Font(os.path.join(HERE, "flash_font.bin"))
    except Exception as e:  # noqa
        log("ERRO ao carregar flash_font.bin:", repr(e))
        return 3

    sdl2.SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER) != 0:
        log("ERRO SDL_Init:", sdl2.SDL_GetError())
        return 3
    sdl2.SDL_ShowCursor(0)

    win = sdl2.SDL_CreateWindow(b"H7Flash SDL - experimental", 0, 0, 640, 480,
                                sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP | sdl2.SDL_WINDOW_SHOWN)
    if not win:
        win = sdl2.SDL_CreateWindow(b"H7Flash SDL - experimental", 0, 0, 640, 480, sdl2.SDL_WINDOW_SHOWN)
    if not win:
        log("ERRO SDL_CreateWindow:", sdl2.SDL_GetError())
        sdl2.SDL_Quit()
        return 3
    surf = sdl2.SDL_GetWindowSurface(win)
    if not surf:
        log("ERRO SDL_GetWindowSurface:", sdl2.SDL_GetError())
        sdl2.SDL_Quit()
        return 3
    W, H = surf.contents.w, surf.contents.h
    log("janela", W, "x", H)

    # controles: GameController (usa SDL_GAMECONTROLLERCONFIG do PortMaster) + joystick cru como reserva
    pads = []
    for i in range(sdl2.SDL_NumJoysticks()):
        if sdl2.SDL_IsGameController(i):
            c = sdl2.SDL_GameControllerOpen(i)
            if c:
                pads.append(c)
                log("controller:", sdl2.SDL_GameControllerName(c))
                continue
        j = sdl2.SDL_JoystickOpen(i)
        if j:
            pads.append(j)
            log("joystick:", sdl2.SDL_JoystickName(j))

    big_w, big_h = font.metrics(0)
    sm_w, sm_h = font.metrics(1)
    top_h = 56
    foot_h = 40
    row_h = big_h + 14
    rows = max(1, (H - top_h - foot_h - 16) // row_h)

    def fill(x, y, w, h, c):
        sdl2.SDL_FillRect(surf, sdl2.SDL_Rect(x, y, w, h), (c[0] << 16) | (c[1] << 8) | c[2])

    first = 0

    def draw():
        nonlocal first
        fill(0, 0, W, H, BG)
        fill(0, 0, W, top_h, BAR)
        fill(0, top_h - 3, W, 3, ACC)
        font.draw(surf, 0, 18, (top_h - 3 - big_h) // 2, "H7Flash SDL", ACC)
        cnt = "%d jogo%s" % (len(games), "" if len(games) == 1 else "s")
        font.draw(surf, 1, W - 18 - font.width(1, cnt), (top_h - 3 - sm_h) // 2, cnt, DIM)

        if not games:
            msg1 = "Nenhum jogo encontrado."
            msg2 = "Coloque arquivos .swf em H7Flash/games"
            font.draw(surf, 0, (W - font.width(0, msg1)) // 2, H // 2 - 30, msg1, TXT)
            font.draw(surf, 1, (W - font.width(1, msg2)) // 2, H // 2 + 6, msg2, DIM)
        else:
            if sel < first:
                first = sel
            if sel >= first + rows:
                first = sel - rows + 1
            y0 = top_h + 8
            textw = W - 2 * 18 - 22
            for r in range(rows):
                i = first + r
                if i >= len(games):
                    break
                y = y0 + r * row_h
                name = fit(games[i][0], 0, font, textw)
                if i == sel:
                    fill(10, y, W - 20 - 14, row_h - 4, ACC)
                    font.draw(surf, 0, 22, y + (row_h - 4 - big_h) // 2, name, WHITE)
                else:
                    font.draw(surf, 0, 22, y + (row_h - 4 - big_h) // 2, name, TXT)
            if len(games) > rows:  # barra de rolagem
                track_h = rows * row_h - 4
                fill(W - 14, y0, 6, track_h, BAR)
                th = max(16, track_h * rows // len(games))
                ty = y0 + (track_h - th) * first // max(1, len(games) - rows)
                fill(W - 14, ty, 6, th, DIM)

        fill(0, H - foot_h, W, foot_h, BAR)
        fill(0, H - foot_h, W, 2, (44, 52, 90))
        hint = "A: Jogar  START: Opcoes  B: Sair"
        if swap:
            hint = "B: Jogar  START: Opcoes  A: Sair"
        font.draw(surf, 1, (W - font.width(1, hint)) // 2, H - foot_h + (foot_h - sm_h) // 2 + 1, hint, DIM)
        sdl2.SDL_UpdateWindowSurface(win)

    def move(d):
        nonlocal sel
        if not games:
            return
        sel = (sel + d) % len(games) if abs(d) == 1 else max(0, min(len(games) - 1, sel + d))

    result = 1
    ev = sdl2.SDL_Event()
    running = True
    held = None        # direcao segurada (-1 / +1) para repeticao
    held_next = 0
    CB = sdl2.SDL_CONTROLLER_BUTTON_A
    last_draw = 0

    def confirm():
        nonlocal result, running
        if games:
            with open(CHOICE_FILE, "w", encoding="utf-8") as f:
                f.write(games[sel][1])
            try:
                with open(LAST_FILE, "w", encoding="utf-8") as f:
                    f.write(os.path.basename(games[sel][1]))
            except OSError:
                pass
            log("escolhido:", games[sel][1])
            result = 0
            running = False

    def options():
        nonlocal held, last_draw
        held = None
        if games and not game_options.run(win, surf, font, games[sel][1], swap): back()
        last_draw = 0

    def back():
        nonlocal result, running
        result = 1
        running = False

    draw()
    while running:
        while sdl2.SDL_PollEvent(ctypes.byref(ev)):
            t = ev.type
            if t == sdl2.SDL_QUIT:
                back()
            elif t == sdl2.SDL_CONTROLLERBUTTONDOWN:
                b = ev.cbutton.button
                log("botao", sdl2.SDL_GameControllerGetStringForButton(b))
                if b == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
                    move(-1); held, held_next = -1, time.time() + 0.35
                elif b == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                    move(1); held, held_next = 1, time.time() + 0.35
                elif b == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT or b == sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:
                    move(-rows)
                elif b == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT or b == sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:
                    move(rows)
                elif b == sdl2.SDL_CONTROLLER_BUTTON_START:
                    options()
                elif b == (sdl2.SDL_CONTROLLER_BUTTON_B if swap else sdl2.SDL_CONTROLLER_BUTTON_A):
                    confirm()
                elif b == (sdl2.SDL_CONTROLLER_BUTTON_A if swap else sdl2.SDL_CONTROLLER_BUTTON_B) \
                        or b in (sdl2.SDL_CONTROLLER_BUTTON_BACK, sdl2.SDL_CONTROLLER_BUTTON_GUIDE):
                    back()
                last_draw = 0
            elif t == sdl2.SDL_CONTROLLERBUTTONUP:
                b = ev.cbutton.button
                if b in (sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN):
                    held = None
            elif t == sdl2.SDL_CONTROLLERAXISMOTION and ev.caxis.axis == sdl2.SDL_CONTROLLER_AXIS_LEFTY:
                v = ev.caxis.value
                if abs(v) > 16000:
                    d = 1 if v > 0 else -1
                    if held != d:
                        move(d); held, held_next = d, time.time() + 0.35
                        last_draw = 0
                elif held is not None and not _dpad_down(pads):
                    held = None
            elif t == sdl2.SDL_JOYHATMOTION and not sdl2.SDL_IsGameController(ev.jhat.which):
                v = ev.jhat.value
                if v & sdl2.SDL_HAT_UP:
                    move(-1)
                elif v & sdl2.SDL_HAT_DOWN:
                    move(1)
                last_draw = 0
            elif t == sdl2.SDL_JOYBUTTONDOWN and not sdl2.SDL_IsGameController(ev.jbutton.which):
                b = ev.jbutton.button
                log("joy botao", b)
                if b == 7:
                    options()
                elif b == (1 if swap else 0):
                    confirm()
                elif b == (0 if swap else 1):
                    back()
            elif t == sdl2.SDL_KEYDOWN:
                k = ev.key.keysym.sym
                if k == sdl2.SDLK_UP:
                    move(-1)
                elif k == sdl2.SDLK_DOWN:
                    move(1)
                elif k == sdl2.SDLK_RETURN:
                    options()
                elif k == sdl2.SDLK_z:
                    confirm()
                elif k in (sdl2.SDLK_ESCAPE, sdl2.SDLK_x):
                    back()
                last_draw = 0

        now = time.time()
        if held and now >= held_next:
            move(held)
            held_next = now + 0.09
            last_draw = 0
        if now - last_draw > 0.5 or last_draw == 0:
            draw()
            last_draw = now
        sdl2.SDL_Delay(16)

    sdl2.SDL_DestroyWindow(win)
    sdl2.SDL_Quit()
    return result


def _dpad_down(pads):
    try:
        for p in pads:
            if sdl2.SDL_GameControllerGetButton(p, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP) or \
               sdl2.SDL_GameControllerGetButton(p, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN):
                return True
    except Exception:  # noqa
        pass
    return False


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:  # noqa
        import traceback
        log("EXCECAO:", traceback.format_exc())
        rc = 3
    log("menu terminou, codigo", rc)
    sys.exit(rc)
