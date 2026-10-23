#include <SDL.h>
#include <SDL_opengles2.h>
#include <stdio.h>
#include <string.h>

/* Use the device's SDL/EGL implementation; do not link a replacement GL driver. */
int main(int argc, char **argv) {
    (void)argc; (void)argv;
    setvbuf(stdout, NULL, _IONBF, 0);
    SDL_version version;
    SDL_GetVersion(&version);
    printf("SDL runtime=%u.%u.%u\n", version.major, version.minor, version.patch);
    for (int i=0; i<SDL_GetNumVideoDrivers(); i++)
        printf("video_driver_available=%s\n", SDL_GetVideoDriver(i));
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER | SDL_INIT_EVENTS)) {
        printf("FAIL SDL_Init: %s\n", SDL_GetError()); return 2;
    }
    printf("video_driver_selected=%s\n", SDL_GetCurrentVideoDriver());
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
    SDL_GL_SetAttribute(SDL_GL_RED_SIZE, 8);
    SDL_GL_SetAttribute(SDL_GL_GREEN_SIZE, 8);
    SDL_GL_SetAttribute(SDL_GL_BLUE_SIZE, 8);
    SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_Window *window=SDL_CreateWindow("H7Flash - teste de tela", SDL_WINDOWPOS_UNDEFINED,
        SDL_WINDOWPOS_UNDEFINED, 640, 480, SDL_WINDOW_OPENGL | SDL_WINDOW_FULLSCREEN_DESKTOP);
    if (!window) {
        printf("FAIL window: %s\n", SDL_GetError()); SDL_Quit(); return 3;
    }
    SDL_GLContext context=SDL_GL_CreateContext(window);
    if (!context) {
        printf("FAIL context: %s\n", SDL_GetError()); SDL_DestroyWindow(window); SDL_Quit(); return 4;
    }
    const GLubyte *(*get_string)(GLenum)=SDL_GL_GetProcAddress("glGetString");
    void (*clear_color)(GLfloat,GLfloat,GLfloat,GLfloat)=SDL_GL_GetProcAddress("glClearColor");
    void (*clear)(GLbitfield)=SDL_GL_GetProcAddress("glClear");
    void (*enable)(GLenum)=SDL_GL_GetProcAddress("glEnable");
    void (*disable)(GLenum)=SDL_GL_GetProcAddress("glDisable");
    void (*scissor)(GLint,GLint,GLsizei,GLsizei)=SDL_GL_GetProcAddress("glScissor");
    int result=0;
    if (!get_string || !clear_color || !clear || !enable || !disable || !scissor) {
        puts("FAIL missing GLES entry point"); result=5; goto cleanup;
    }
    const char *renderer=(const char *)get_string(GL_RENDERER);
    const char *vendor=(const char *)get_string(GL_VENDOR);
    const char *gl_version=(const char *)get_string(GL_VERSION);
    printf("GL_VENDOR=%s\nGL_RENDERER=%s\nGL_VERSION=%s\n",
        vendor ? vendor : "unknown", renderer ? renderer : "unknown", gl_version ? gl_version : "unknown");
    if (!renderer || strstr(renderer,"llvmpipe") || strstr(renderer,"softpipe") || strstr(renderer,"SwiftShader")) {
        puts("FAIL no confirmed hardware renderer"); result=6; goto cleanup;
    }
    printf("swap_interval_result=%d\n",SDL_GL_SetSwapInterval(1));
    SDL_Joystick *joysticks[8]={0};
    int devices=SDL_NumJoysticks();
    printf("joysticks=%d\n",devices);
    for (int i=0; i<devices && i<8; i++) {
        joysticks[i]=SDL_JoystickOpen(i);
        const char *name=SDL_JoystickNameForIndex(i);
        printf("joystick[%d]=%s opened=%d\n",i,name ? name : "unknown",joysticks[i]!=NULL);
    }
    int width,height;
    SDL_GL_GetDrawableSize(window,&width,&height);
    printf("drawable=%dx%d; running for 12 seconds; press buttons to record input\n",width,height);
    Uint32 start=SDL_GetTicks();
    unsigned frames=0, inputs=0;
    double swap_total=0,swap_max=0;
    int running=1;
    while (running && SDL_GetTicks()-start<12000) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type==SDL_QUIT) running=0;
            if (event.type==SDL_KEYDOWN) {
                printf("key=%d\n",event.key.keysym.sym); inputs++;
                if (event.key.keysym.sym==SDLK_ESCAPE) running=0;
            }
            if (event.type==SDL_JOYBUTTONDOWN) {
                printf("joy_button=%u\n",event.jbutton.button); inputs++;
            }
        }
        disable(GL_SCISSOR_TEST); clear_color(0.03f,0.08f,0.12f,1); clear(GL_COLOR_BUFFER_BIT);
        enable(GL_SCISSOR_TEST);
        scissor(0,height/3,width/3,height/3); clear_color(0.9f,0.1f,0.1f,1); clear(GL_COLOR_BUFFER_BIT);
        scissor(width/3,height/3,width/3,height/3); clear_color(0.1f,0.9f,0.1f,1); clear(GL_COLOR_BUFFER_BIT);
        scissor(2*width/3,height/3,width/3,height/3); clear_color(0.1f,0.2f,0.9f,1); clear(GL_COLOR_BUFFER_BIT);
        scissor((int)((SDL_GetTicks()-start)/4 % (unsigned)(width>0?width:1)),0,12,height/4);
        clear_color(inputs ? 0.1f : 1.0f,1.0f,1.0f,1); clear(GL_COLOR_BUFFER_BIT);
        Uint64 before=SDL_GetPerformanceCounter();
        SDL_GL_SwapWindow(window);
        double elapsed=(SDL_GetPerformanceCounter()-before)*1000.0/SDL_GetPerformanceFrequency();
        swap_total+=elapsed; if (elapsed>swap_max) swap_max=elapsed;
        frames++; SDL_Delay(8);
    }
    printf("PASS context_and_loop frames=%u inputs=%u swap_avg_ms=%.3f swap_max_ms=%.3f\n",
        frames,inputs,frames?swap_total/frames:0,swap_max);
    puts("This is a display smoke test, not a Flash performance benchmark. Visible output requires user confirmation.");
    for (int i=0; i<devices && i<8; i++) if (joysticks[i]) SDL_JoystickClose(joysticks[i]);
cleanup:
    SDL_GL_DeleteContext(context); SDL_DestroyWindow(window); SDL_Quit();
    return result;
}
