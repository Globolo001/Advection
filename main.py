
if __name__ == "__main__":
    import sys
    # Pre-initialize numba (and its C extensions) before pygame loads on macOS ARM.
    # Without this, numba's lazy C extension loading races with pygame's Cocoa thread
    # state changes, causing a fatal GIL error (SIGABRT / exit 134).
    import numba  # noqa: F401

    def graceful_shutdown():
        """Clean up pygame and destroy the tkinter window."""
        import pygame as pg
        pg.quit()
        try:
            interface.UI.TkApp.destroy()
        except Exception:
            pass
        sys.exit(0)

    def loop():
        try:
            PygameRenderer.loop()
            interface.UI.TkApp.update_idletasks()
        except Exception:
            pass  # Guard against customtkinter widget lifecycle errors
        interface.UI.TkApp.after(15, loop)

    import src.frontend.interface as interface
    import src.frontend.renderer as preview

    from src.shared.variables import *
    PygameRenderer = preview.PygameRender(AppConstants.WIDTH/2, AppConstants.HEIGHT/5*4, interface.UI.preview_frame)
    PygameData.PygameRenderer = PygameRenderer

    # Graceful shutdown on Cmd-W (macOS) and window close
    if sys.platform == 'darwin':
        interface.UI.TkApp.bind('<Command-w>', lambda e: graceful_shutdown())
    interface.UI.TkApp.protocol("WM_DELETE_WINDOW", graceful_shutdown)

    interface.UI.try_update_input('src/assets/Advection_3d_logo.obj')

    loop()
    interface.UI.TkApp.mainloop()















