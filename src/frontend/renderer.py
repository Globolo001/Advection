from src.frontend.rendering.object_3d import *
from src.frontend.rendering.camera import *
from src.frontend.rendering.projection import *
import src.frontend.rendering.texture_data as td
from src.shared.variables import *
from src.frontend.textured_particle import *
import pygame as pg
from os import environ as os_environ
import sys
from typing import TYPE_CHECKING

_IS_MACOS = sys.platform == 'darwin'

if _IS_MACOS or TYPE_CHECKING:
    import tkinter as tk
    from PIL import Image, ImageTk

if _IS_MACOS:
    os_environ['SDL_VIDEODRIVER'] = 'dummy'

class PygameRender:
    def __init__(self,WIDTH, HEIGHT, frame):
        self.frame = frame
        self.RES = self.WIDTH, self.HEIGHT = int(WIDTH), int(HEIGHT)
        self.H_WIDTH, self.H_HEIGHT = self.WIDTH // 2, self.HEIGHT // 2
        self.aspect_ratio = self.WIDTH / self.HEIGHT
        self.FPS = 60

        if sys.platform == 'win32':
            os_environ['SDL_WINDOWID'] = str(frame.winfo_id())
            os_environ['SDL_VIDEODRIVER'] = 'windib'

        pg.display.init()
        self.screen = pg.display.set_mode(self.RES)
        if not _IS_MACOS and sys.platform != 'win32':
            pg.display.set_caption('Advection - Preview')

        if _IS_MACOS:
            self._canvas = tk.Canvas(frame, bg='black', highlightthickness=0)
            self._canvas.pack(fill='both', expand=True)
            self._photo = None
            self._bind_canvas_events()

        self.clock = pg.time.Clock()
        pg.font.init()

        self.InterFont = pg.font.SysFont('Inter', 13)

        td.load_textures()
        td.load_atlas_animations()

        self.set_particles_texture(ParticleData.particle_type.get()) # Define the texture used of render
        self.create_object()

        self.last_mouse_pos = None
        self.panning_active = False
        self.pan_last_mouse_pos = None


    def set_particles_texture(self, texture_name):
        PygameData.texture = td.solo_textures[f"{texture_name}"]
        PygameData.textures = td.atlas_frames[f"{texture_name}"]


    def create_object(self):
        self.camera = Camera(self, AppConstants.DEFAULT_CAMERA_POSITION, AppConstants.DEFAULT_CAMERA_PITCH_YAW_ROLL) # Initialize the camera
        self.projection = Projection(self,self.aspect_ratio) # Instanciate the projection

        self.world_axes = Axes(self)
        self.world_axes.movement_flag = False

    def reset_camera(self):
        self.camera = Camera(self, AppConstants.DEFAULT_CAMERA_POSITION,AppConstants.DEFAULT_CAMERA_PITCH_YAW_ROLL)
        PygameTempData.update_requested += 1

    def frame_model(self, cloud):
        """Position the camera so the loaded model is visible and centered."""
        import math as _math
        center = cloud.center  # (cx, cy, cz)
        size = cloud.size      # (sx, sy, sz)
        max_dim = max(abs(s) for s in size) if any(size) else 1.0
        # Distance so the model fits in view (h_fov = pi/3)
        dist = max_dim / _math.tan(_math.pi / 6) * 1.2
        # Camera looks in +Z, so place it behind (negative Z) from model center
        # After modifiers with alignment='None': model X,Y at original center, Z centered at 0
        cam_x = float(center[0])
        cam_y = float(center[1])
        cam_z = -dist
        self.camera = Camera(self, [cam_x, cam_y, cam_z], (0, 0, 0))
        PygameTempData.update_requested += 5

    def draw_frame(self):
        self.world_axes.draw()
        if ParticlesCache.TexturedParticlesCloud:
            ParticlesCache.TexturedParticlesCloud.draw(self)

    def refresh_cloud_stats(self):
        self.cloud_count = ParticlesCache.TexturedParticlesCloud.count
        if self.cloud_count > 10000:
            color = (255,0,0)
        else:
            color = (255,255,255)
        self.cloud_count_display = self.InterFont.render(f'Count: {self.cloud_count}', True, color)

        
    def loop(self):

        self.clock.tick()
        self.FPS = self.clock.get_fps()


        # Get the events (POSITION IS IMPORTANT, can conflict with tkinter otherwise)
        self.pg_events = pg.event.get() 

        self.inputs_and_events()

        [exit() for i in self.pg_events if i.type == pg.QUIT]

        
        # if PygameTempData.input_detected : # Only update render if input has been detected
        #     self.render_new_frame()
        if PygameTempData.update_requested >= 1 and ParticlesCache.TexturedParticlesCloud:
            ParticlesCache.TexturedParticlesCloud.modifiers = Modifiers() # Update the modifiers only when needed
            self.render_new_frame()
            PygameTempData.update_requested -= 1


    def render_new_frame(self):

        self.screen.fill(pg.Color('gray9'))

        if PygameData.toggle_render.get() == 1:
            self.draw_frame()
            self.screen.blit(self.InterFont.render(f'FPS: {round(self.FPS)}', True, (255, 255, 255)), (10, 50))

        self.screen.blit(self.cloud_count_display, (10, 30))

        pg.display.flip()
        if _IS_MACOS:
            self._update_tkinter_display()



    def inputs_and_events(self):

        # On macOS, also check for canvas resize
        if _IS_MACOS:
            cw = self._canvas.winfo_width()
            ch = self._canvas.winfo_height()
            if cw > 1 and ch > 1 and (cw != self.WIDTH or ch != self.HEIGHT):
                self.WIDTH, self.HEIGHT = cw, ch
                self.RES = (self.WIDTH, self.HEIGHT)
                self.screen = pg.Surface(self.RES)
                pg.event.post(pg.event.Event(pg.VIDEORESIZE, w=cw, h=ch))

        for event in self.pg_events:
            if event.type == pg.VIDEORESIZE:
                if sys.platform == 'win32':
                    self.H_WIDTH, self.H_HEIGHT = self.frame.winfo_width() // 2, self.frame.winfo_height() // 2
                else:
                    self.H_WIDTH, self.H_HEIGHT = event.w // 2, event.h // 2
                self.aspect_ratio =  self.H_WIDTH / self.H_HEIGHT
                self.projection = Projection(self,self.aspect_ratio)
                PygameTempData.update_requested += 5 # Several frames to be sure it updates (also responsible of the initial refresh)
            if event.type == pg.MOUSEBUTTONDOWN:
                # if self.starting:
                #     self.starting = False
                PygameTempData.update_requested = 1
                if event.button == 3:  # Right mouse button
                    self.last_mouse_pos = event.pos
                elif event.button == 2:  # Middle mouse button for pan
                    self.panning_active = True
                    self.pan_last_mouse_pos = event.pos

            if event.type == pg.MOUSEMOTION:
                if self.last_mouse_pos:  # Rotate camera with left mouse
                    PygameTempData.update_requested = 1
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]

                    self.camera.input_rotation(dx, dy)
                    self.last_mouse_pos = event.pos
                elif self.panning_active:  # Pan camera with middle mouse
                    PygameTempData.update_requested = 1

                    input_lateral_motion = event.pos[0] - self.pan_last_mouse_pos[0]
                    input_vertical_motion = event.pos[1] - self.pan_last_mouse_pos[1]
                    self.camera.input_movement(input_lateral_motion, input_vertical_motion)
                    self.pan_last_mouse_pos = event.pos

            if event.type == pg.MOUSEBUTTONUP:
                if event.button == 3:   # Right mouse button released
                    self.last_mouse_pos = None
                elif event.button == 2:  # Middle mouse button released
                    self.panning_active = False
                    self.pan_last_mouse_pos = None

            if event.type == pg.MOUSEWHEEL:
                PygameTempData.update_requested = 1
                zoom = event.y
                self.camera.input_zoom(zoom)

    def DataParticlesCloud_to_TexturedParticlesCloud(self, dataParticlesCloud):
        """Converts a DataParticlesCloud instance to a TexturedParticlesCloud instance."""
        return TexturedParticlesCloud( dataParticlesCloud, PygameData.textures)

    # --- macOS offscreen rendering helpers ---

    def _update_tkinter_display(self):
        """Copy the pygame surface to the tkinter canvas via PIL."""
        raw = pg.image.tobytes(self.screen, 'RGB')
        img = Image.frombytes('RGB', self.screen.get_size(), raw)
        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete('all')
        self._canvas.create_image(0, 0, anchor='nw', image=self._photo)

    def _bind_canvas_events(self):
        """Bridge tkinter Canvas mouse events to the pygame event queue on macOS.

        Mappings:
        - Left-click drag (Button-1): orbit (camera rotation)
        - Right-click drag (Button-2 / two-finger): pan
        - Option+click drag: pan (alternative for trackpad users)
        - Scroll: zoom
        """
        c = self._canvas

        # Give focus to canvas on click so it receives events
        c.bind('<ButtonPress-1>', self._on_canvas_click)

        # Left mouse button → orbit (pygame button=3)
        c.bind('<ButtonPress-1>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEBUTTONDOWN, button=3, pos=(e.x, e.y))))
        c.bind('<ButtonRelease-1>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEBUTTONUP, button=3, pos=(e.x, e.y))))
        c.bind('<B1-Motion>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEMOTION, pos=(e.x, e.y), rel=(0, 0), buttons=(0, 0, 0))))

        # Right-click (Button-2 on macOS) → pan (pygame button=2)
        c.bind('<ButtonPress-2>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEBUTTONDOWN, button=2, pos=(e.x, e.y))))
        c.bind('<ButtonRelease-2>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEBUTTONUP, button=2, pos=(e.x, e.y))))
        c.bind('<B2-Motion>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEMOTION, pos=(e.x, e.y), rel=(0, 0), buttons=(0, 0, 0))))

        # Context menu button (Button-3) → also pan
        c.bind('<ButtonPress-3>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEBUTTONDOWN, button=2, pos=(e.x, e.y))))
        c.bind('<ButtonRelease-3>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEBUTTONUP, button=2, pos=(e.x, e.y))))
        c.bind('<B3-Motion>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEMOTION, pos=(e.x, e.y), rel=(0, 0), buttons=(0, 0, 0))))

        # Mouse wheel → zoom (normalize macOS delta)
        c.bind('<MouseWheel>', lambda e: pg.event.post(
            pg.event.Event(pg.MOUSEWHEEL, y=1 if e.delta > 0 else -1, x=0)))

    def _on_canvas_click(self, event):
        """Ensure the canvas gets keyboard focus when clicked."""
        self._canvas.focus_set()
