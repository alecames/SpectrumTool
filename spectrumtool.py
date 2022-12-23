from pyaudio import PyAudio, paInt16
import numpy as np
import sys
import pygame
from os import path, makedirs
from math import log, exp, floor
from datetime import datetime
from scipy.io.wavfile import write
from numba import jit
from pygame import gfxdraw

# Created by Alec Ames
# #6843577
# COSC 4P98 - Final Project
# Brock University 11/19/22
# Version 1.4
#
# This application is a spectrum analyzer that displays the frequency spectrum of an audio stream in real-time.
# Features ------------------------------------------------------
# - Toggle between lines and solid spectrum view
# - Toggle microphone on/off
# - Toggle mute/unmute
# - Freeze the spectrum
# - Frequency shifter
# - Hard clip distortion effect
# - Gain control
# - Keybind Menu
# - Dynamic resizing/rescaling
# - Record audio to .wav file
#
# Keybinds & Controls ---------------------------------------------
# Click and drag a knob to adjust its value OR Scroll with mouse wheel over a knob to adjust its value
# Click on a button to toggle its state
# - 'ESC' to quit
# - 'V' to toggle between lines and solid spectrum view
# - 'N' to toggle microphone on/off
# - 'M' to toggle mute/unmute
# - 'F' to freeze the spectrum
# - 'R' to record audio to .wav file
# - 'SHIFT' + Click to reset a knob to its default value
# - 'CTRL' + Click to allow finer control of a knob
# - Right click on FREEZE to toggle freeze mode (other parameters can be adjusted while frozen)

# ---------------------------- CONFIG ----------------------------
# ui settings
FPS = 165
TITLE = "SpectrumTool"
FONT_COLOR = (255, 255, 255)
FONT_COLOR_ACCENT = (200, 255, 200)
SCALE = 1.2
CH_COLOR = (139, 178, 112, 100)
UNIT = 800/7
CTRL_BAR_COLOR = (34, 36, 30)
CTRL_IDLE = (139, 178, 112)
VIEW_BUTTON_COLOR = (73, 102, 60)
MIC_BUTTON_COLOR = (235, 110, 100)
FREEZE_BUTTON_COLOR = (175, 255, 255)
CTRL_CLICKED = (200, 255, 200)
CTRL_HOVER_COLOR = (80, 120, 80)
TIERTIARY_COLOR = (63, 74, 52)
BACKGROUND_COLOR = (27, 27, 27)
SPECTRUM_COLOR = (139, 178, 112)
LINE_COLOR = (255, 255, 255, 12)

# audio settings
DECAY = 4 # how many frames for the spectrum to decay
RATE = 44100 # sample rate
BUFFER = 1024 # buffer size
RESOLUTION = 44100 # resolution of the spectrum
MIN_FREQ = 20 # min freq to display
MAX_FREQ = RATE / 2 # max freq to display
MIN_INT, MAX_INT = -32768, 32767

# ---------------------------- CLASSES ----------------------------
class Knob:
	def __init__(self, min, max, text, value, percent=True):
		self.color = CTRL_IDLE
		self.value_color = CTRL_IDLE
		self.alt_color = TIERTIARY_COLOR
		self.min = min
		self.max = max
		self.text = text
		self.value = value
		self.default = value
		self.current_value = value
		self.dragging = False
		self.sensitivity = 3
		self.percent = percent
		self.rect = pygame.Rect(0, 0, 0, 0)

	def handle_event(self, event, mouse_pos):
		if self.rect.collidepoint(mouse_pos):
			self.color = CTRL_HOVER_COLOR
			if event.type == pygame.MOUSEWHEEL:
				if event.y > 0:
					self.value += 5 * self.max / 270
				else:
					self.value -= 5 * self.max / 270
				self.value = np.clip(self.value, self.min, self.max)
			if event.type == pygame.MOUSEBUTTONDOWN:
				self.dragging = True
				self.color = CTRL_CLICKED
				self.initial_mouse_pos = mouse_pos
				self.current_value = self.value
				if pygame.key.get_mods() & pygame.KMOD_SHIFT:
					self.value = self.default
		if event.type == pygame.MOUSEBUTTONUP:
			self.dragging = False
			self.color = CTRL_IDLE
		if self.dragging:
			diff = mouse_pos[1] - self.initial_mouse_pos[1]
			if diff != 0:
				if pygame.key.get_mods() & pygame.KMOD_CTRL:
					self.sensitivity = 15
				else:
					self.sensitivity = 3
				self.value = self.current_value - (diff / self.sensitivity * self.max / self.rect.height)
				self.value = np.clip(self.value, self.min, self.max)
				self.color = CTRL_CLICKED
				self.value_color = CTRL_CLICKED
		else: 
			self.color = CTRL_IDLE
			self.value_color = CTRL_IDLE

	def draw(self, screen, x, y, r):
		x, y, r = int(x), int(y), int(r)
		self.font_value = pygame.font.Font(FONT_PATH, round(SCALE*r/1.66))
		self.font_label = pygame.font.Font(FONT_PATH, round(SCALE*r/3.33))
		self.rect = pygame.Rect(x - r, y - r, r * 2, r * 2)
		self.angle_value = floor(135 + ((self.value - self.min) * 270 / (self.max - self.min)))
		if self.percent:
			text_rect = self.font_value.render(f"{int(((self.value - self.min)/((self.max - self.min))*100))}", True, self.value_color)
		else:
			text_rect = self.font_value.render(f"{int(self.value - shift_max/2)}", True, self.value_color)
		label_rect_text = self.font_label.render(self.text, True, self.alt_color)
		gfxdraw.arc(screen, x, y, r, 135, 405, self.alt_color)
		gfxdraw.arc(screen, x, y, r, 135, self.angle_value, self.color)
		screen.blit(label_rect_text, (x - (label_rect_text.get_width()/2), y + (r * 0.66)))
		screen.blit(text_rect, (x - (text_rect.get_width()/2), y - text_rect.get_height()/2))

class Button:
	def __init__(self, text, value, keybind=None, toggle=True, alt_text="", clicked_color=CTRL_CLICKED, idle_color=CTRL_IDLE):
		self.toggle = toggle
		self.value = value
		self.keybind = keybind
		self.color_map = {True: clicked_color,False: idle_color}
		alt_text = text if alt_text == "" else alt_text
		self.text_map = {True: text, False: alt_text}
		self.text = self.text_map[self.value]
		self.color = self.color_map[value]
		self.rect = pygame.Rect(0, 0, 0, 0)

	def handle_event(self, event, mouse_pos):
		if self.rect.collidepoint(mouse_pos):
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if self.toggle: self.value = not self.value
				else: self.value = True
			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
				if not self.toggle: 
					self.value = not self.value
			if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				if not self.toggle: self.value = False
		if event.type == pygame.KEYDOWN: 
			if event.key == self.keybind:
				if self.toggle: self.value = not self.value
				else: self.value = True
		elif event.type == pygame.KEYUP:
			if event.key == self.keybind:
				if not self.toggle: self.value = False
		self.color = self.color_map[self.value]
		self.text = self.text_map[self.value]

	def draw(self, screen, x, y, r):
		x,y,r = int(x), int(y), int(r)
		self.font = pygame.font.Font(FONT_PATH, round(SCALE*r/2.5))
		self.rect = pygame.Rect(x - r, y - r, r * 2, r * 2)
		self.text_rect = self.font.render(self.text, True, self.color)
		gfxdraw.aacircle(screen, x, y, r, self.color)
		screen.blit(self.text_rect, (x - (self.text_rect.get_width()/2), y - self.text_rect.get_height()/2))

# ------------------------------ FUNCTIONS ------------------------------ #
def get_font_path():
	if getattr(sys, 'frozen', False):
		font_path = path.join(sys._MEIPASS, "assets/Product Sans Regular.ttf")
	else:
		font_path = "assets/Product Sans Regular.ttf"
	return font_path

def get_icon_path():
	if getattr(sys, 'frozen', False):
		icon_path = path.join(sys._MEIPASS, "assets/icon.png")
	else:
		icon_path = "assets/icon.png"
	return icon_path

def get_note_map():
	note_map = {}
	if getattr(sys, 'frozen', False):
		file_path = path.join(sys._MEIPASS, "assets/note.map")
	else:
		file_path = "assets/note.map"
	with open(file_path, "r") as f:
		for line in f:
			line = line.split()
			note_map[int(line[0])] = line[1]
	return note_map

def save_confirmation(screen, filename): 
	global frame_index
	frame_max = 100
	if frame_index < frame_max:
		if frame_index < (frame_max*2/3):
			alpha = 150
		else:
			alpha = 150-(((frame_index-(frame_max*2/3))**2)/(frame_max/10))
		draw_text(f"Saved file to {filename}", font_tiny, info.current_w/2, info.current_h - UNIT - SCALE*16, align="center", color=FONT_COLOR, alpha=alpha)
		frame_index += 1

def create_log_scale():
	log_min_freq, log_max_freq = log(MIN_FREQ), log(MAX_FREQ)
	log_freqs = [log_min_freq + i * (log_max_freq - log_min_freq) / info.current_w for i in range(info.current_w)]
	freqs = [exp(f) for f in log_freqs]
	return freqs

def draw_spectrum(screen, previous_spectrums, info, spectrum_h_range, freqs, freqs_tuple):
	y = 0
	for s in previous_spectrums[::-1]:
		points = [(x * info.current_w / len(freqs), y * (value / DECAY) + spectrum_h_range - value) for (x, f), value in zip(freqs_tuple, s)]
		if view_button.value:
			pygame.draw.aalines(screen, SPECTRUM_COLOR, False, points, 1)
		else:
			points[0] = (0, spectrum_h_range)
			points[-1] = (info.current_w, spectrum_h_range)
			pygame.draw.polygon(screen, SPECTRUM_COLOR, points)
		y += 1

def draw_text(text, font, x, y, align="center", color=FONT_COLOR, alpha=255):
	rendered_text = font.render(text, True, color)
	text_rect = rendered_text.get_rect()
	if align == "center":
		text_rect.center = (x, y)
	elif align == "left":
		text_rect.center = (int(x + rendered_text.get_width()/2), y)
	elif align == "right":
		text_rect.center = (int(x - rendered_text.get_width()/2), y)
	rendered_text.set_alpha(alpha)
	screen.blit(rendered_text, text_rect)

# main event loop
def note_equivalent(note_map, tmp_freq):
	freq = tmp_freq
	note = int(round(12 * np.log2(freq / 440) + 69))
	if note in note_map:
		notename = note_map[note]
	else:
		notename = ""
	return freq,notename

def save_file(output_file):
	timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
	out_file_name = f'out/recorded_audio_{timestamp}.wav'
	if not path.exists('out'):
		makedirs('out')
	write(out_file_name, 44100, output_file)
	output_file = None
	return out_file_name

def draw_keybinds(screen):
	draw_text("KEYBINDS", font_medium, info.current_w/2, info.current_h/2 - (SCALE * info.current_h/3.5))
	draw_text("Click the title again to close this menu", font_tiny, info.current_w/2, info.current_h/2 - (SCALE * info.current_h/3.5) + (SCALE * 30))
	draw_text("Hold CTRL to fine-tune knobs", font_xtiny, info.current_w - SCALE * 5, info.current_h - UNIT - SCALE * 34, color=CTRL_CLICKED, align="right")
	draw_text("Hold SHIFT to reset knob to defaults", font_xtiny, info.current_w - SCALE * 5, info.current_h - UNIT - SCALE * 22, color=CTRL_CLICKED, align="right")
	draw_text("Right click on FREEZE button to toggle freeze mode", font_xtiny, info.current_w - SCALE * 5, info.current_h - UNIT - SCALE * 10 , color=CTRL_CLICKED, align="right")
	pygame.draw.line(screen, FONT_COLOR, (info.current_w/2 - (SCALE * 100), info.current_h/2 - (SCALE * info.current_h/3.5) + (SCALE * 45)), (info.current_w/2 + (SCALE * 100), info.current_h/2 - (SCALE * info.current_h/3.5) + (SCALE * 45)), 1)
	keybinds = [
		("View", "V", "Toggle view"),
		("Mute", "M", "Toggle mute"),
		("Mic", "N", "Toggle mic"),
		("Freeze", "F", "Freeze spectrum"),
		("Record", "R", "Record audio to .wav file"), 
		("Quit", "ESC", "Close the application")]
	for i, keybind in enumerate(keybinds):
		keybind_text = font_tiny.render(f"{keybind[0]} [{keybind[1]}] - {keybind[2]}", True, FONT_COLOR)
		keybind_rect = keybind_text.get_rect()
		keybind_rect.center = (info.current_w/2, info.current_h/2 - (SCALE * info.current_h/3.5) + (SCALE * 60) + (SCALE * 20 * i))
		screen.blit(keybind_text, keybind_rect)
# ------------------------------ AUDIO FX ------------------------------ #
@jit(nopython=True)
def gain(in_data, gain):
	out_data = in_data * gain
	return out_data

def dist_fx(in_data, amount):
	out_data = in_data
	if amount == 1: return out_data
	out_data = np.clip(out_data, MIN_INT/amount, MAX_INT/amount)
	out_data = out_data * (amount + 10)/12
	out_data = np.clip(out_data, MIN_INT, MAX_INT)
	return out_data

def freq_shift_delay_fx(in_data, shift):
	out_data = in_data
	fft_data = np.fft.rfft(out_data)
	fft_data = np.roll(fft_data, int(shift - shift_max/2))
	out_data = np.fft.irfft(fft_data)
	return out_data


# ---------------------------- MAIN ---------------------------- #
pygame.init() 
screen = pygame.display.set_mode((800, 500), pygame.RESIZABLE)
FONT_PATH = get_font_path() # font by Google https://befonts.com/product-sans-font.html
pygame.display.set_caption(TITLE)
icon = pygame.image.load(get_icon_path()) # application icon by Icons8 https://icons8.com
pygame.display.set_icon(icon)
audio_data = np.zeros(BUFFER)

# init audio streams for in and out
p = PyAudio()
mic_stream = p.open(format=paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=BUFFER)
out_stream = p.open(format=paInt16, channels=1, rate=RATE, output=True, frames_per_buffer=BUFFER)

# init variables
previous_spectrums = []
shift_max = 48
peak_freq = 0
peak_notename = ""
show_keybinds = False
output_file = None
frame_index = 0
out_file_name = None

# init fonts
font_xtiny = pygame.font.Font(FONT_PATH, round(SCALE* 10))
font_tiny = pygame.font.Font(FONT_PATH, round(SCALE* 12))
font_small = pygame.font.Font(FONT_PATH, round(SCALE* 16))
font_medium = pygame.font.Font(FONT_PATH, round(SCALE* 20))
font_large = pygame.font.Font(FONT_PATH, round(SCALE* 28))

# init buttons and knobs
view_button = Button("LINE", True, pygame.K_v, alt_text="SOLID", idle_color=CTRL_CLICKED, clicked_color=CTRL_CLICKED)
mic_button = Button("MIC", True, pygame.K_n, idle_color=TIERTIARY_COLOR, clicked_color=MIC_BUTTON_COLOR)
mute_button = Button("MUTE", False, pygame.K_m, idle_color=TIERTIARY_COLOR, clicked_color=CTRL_CLICKED)
gain_knob = Knob(0, 1.2, "GAIN", 0.8)
dist_knob = Knob(1, 512, "DIST", 1)
freq_shift_knob = Knob(0, shift_max, "SHIFT", shift_max/2, percent=False)
record_button = Button("REC", False, pygame.K_r, idle_color=CTRL_IDLE, clicked_color=MIC_BUTTON_COLOR)
freeze_button = Button("FREEZE", False, pygame.K_f, toggle=False, clicked_color=FREEZE_BUTTON_COLOR)

note_map = get_note_map()

while True:
	if not freeze_button.value: # freeze the spectrum (and audio)
		data = mic_stream.read(BUFFER)
		if not mic_button.value: # mute mic
			data = b'\x00' * BUFFER
	audio_data = np.frombuffer(data, dtype=np.int16)

	# effects chain
	audio_data = dist_fx(audio_data, dist_knob.value)
	audio_data = freq_shift_delay_fx(audio_data, freq_shift_knob.value)
	audio_data = gain(audio_data, gain_knob.value)

	# fft for spectrum visualization
	spectrum = np.abs(np.fft.rfft(audio_data, n=RESOLUTION))

	# visual representation of spectrum
	info = pygame.display.Info()
	spectrum_h_range = info.current_h - UNIT # compensate for the control bar
	dp_spectrum = spectrum
	freqs = create_log_scale()
	freqs_tuple = [(x, f) for x, f in enumerate(freqs)]
	dp_spectrum = np.interp(freqs, np.linspace(0, MAX_FREQ, len(dp_spectrum)), dp_spectrum)
	dp_spectrum /= (2 ** 18) # scales down spectrum to fit on screen
	if np.max(dp_spectrum) > 1: 
		dp_spectrum /= np.max(dp_spectrum)
	dp_spectrum *= spectrum_h_range * 0.95 # prevents from touching the top of the screen

	previous_spectrums.append(dp_spectrum) # adds spectrum to list of previous spectrums (for decay)
	if len(previous_spectrums) > DECAY: # pops off the oldest spectrum if the list is too long
		previous_spectrums.pop(0)

	# draws spectrum
	screen.fill(BACKGROUND_COLOR)
	draw_text(TITLE, font_large, SCALE * 10, SCALE * 20, color=TIERTIARY_COLOR, align="left")
	draw_text("by Alec Ames", font_tiny, SCALE * 32, SCALE * 37, color=TIERTIARY_COLOR, align="left")
	draw_spectrum(screen, previous_spectrums, info, spectrum_h_range, freqs, freqs_tuple)

	# audio data to output stream
	if record_button.value: 
		if output_file is None:
			output_file = np.int16(audio_data)/(RATE/4)
		else:
			output_file = np.append(output_file, np.int16(audio_data)/(RATE/4))
	elif output_file is not None:
		frame_index = 0
		out_file_name = save_file(output_file)
		output_file = None
	if out_file_name is not None:
		save_confirmation(screen, out_file_name)
	if not mute_button.value:
		out_stream.write(np.int16(audio_data).tobytes())

	# ------------------------------ UI ------------------------------ #
	# mic on/off indicator
	if mic_button.value: mode_string = "MIC ON"
	else: mode_string = "MIC OFF"
	mode_text = font_medium.render(mode_string, True, FONT_COLOR)
	screen.blit(mode_text, (info.current_w - (mode_text.get_width() + (SCALE * 10)),  (SCALE * 10)))

	# only shows mouse cursor if in window
	mouse_pos = pygame.mouse.get_pos()
	try: 
		if mouse_pos[1] < spectrum_h_range:
			mouse_freq, mouse_note = note_equivalent(note_map, int(freqs[mouse_pos[0]]))
			pygame.draw.line(screen, CH_COLOR, (mouse_pos[0], 0), (mouse_pos[0], spectrum_h_range), 1)
			freq_text = font_small.render(f"{mouse_freq} Hz", True, FONT_COLOR)
			screen.blit(freq_text, (max(mouse_pos[0] - freq_text.get_width() - 15, 0 + (SCALE * 10)), max(mouse_pos[1] - (SCALE * 10), SCALE * 75)))
			note_text = font_tiny.render(f"{mouse_note}", True, FONT_COLOR)
			screen.blit(note_text, (max(mouse_pos[0] - note_text.get_width() - 15, 0 + (SCALE * 10)), max(mouse_pos[1] - (SCALE * 10), SCALE * 75) + freq_text.get_height()))
	except IndexError:
		pass

	# peak freq indicator
	peak_freq_text = font_small.render(f"{int(peak_freq)} Hz", True, FONT_COLOR)
	peak_note_text = font_small.render(f"{peak_notename}", True, FONT_COLOR)
	temp_peak_freq = freqs[np.argmax(dp_spectrum)]
	if np.max(dp_spectrum) > 30 and temp_peak_freq > 60: # filter out low freq and low amplitude noise
		peak_freq, peak_notename = note_equivalent(note_map, temp_peak_freq)
		peak_freq_text = font_small.render(f"{int(peak_freq)} Hz", True, FONT_COLOR_ACCENT)
		peak_note_text = font_small.render(f"{peak_notename}", True, FONT_COLOR_ACCENT)
		screen.blit(peak_freq_text, (info.current_w - (peak_freq_text.get_width() + (SCALE * 10)), (SCALE * 35)))
		screen.blit(peak_note_text, (info.current_w - (peak_note_text.get_width() + (SCALE * 10)), (SCALE * 55)))
	else: 
		screen.blit(peak_freq_text, (info.current_w - (peak_freq_text.get_width() + (SCALE * 10)), (SCALE * 35)))
		screen.blit(peak_note_text, (info.current_w - (peak_note_text.get_width() + (SCALE * 10)), (SCALE * 55)))

	# keybind popup
	if show_keybinds: draw_keybinds(screen)	

	# draw control bar
	pygame.draw.rect(screen, CTRL_BAR_COLOR, (0, info.current_h - UNIT, info.current_w, UNIT))
	pygame.draw.line(screen, TIERTIARY_COLOR, (0, (info.current_h - UNIT) + 1), (info.current_w + 1, info.current_h - UNIT + 1), 2)

	radius = UNIT/3
	gap = radius*2.5

	# draw buttons and knobs
	view_button.draw(screen, UNIT/2, (info.current_h - UNIT/2), radius)
	mic_button.draw(screen, UNIT/2 + gap, (info.current_h - UNIT/2), radius)
	mute_button.draw(screen, UNIT/2 + gap*2, (info.current_h - UNIT/2), radius)
	freeze_button.draw(screen, UNIT/2 + gap*3, info.current_h - UNIT/2, radius)
	record_button.draw(screen, UNIT/2 + gap*4, info.current_h - UNIT/2, radius)
	freq_shift_knob.draw(screen, info.current_w - UNIT/2 - gap*2, (info.current_h - UNIT/2), radius)
	dist_knob.draw(screen, info.current_w - UNIT/2 - gap, (info.current_h - UNIT/2), radius)
	gain_knob.draw(screen, info.current_w - UNIT/2, (info.current_h - UNIT/2), radius)

	# --------------------- EVENTS --------------------- #
	pygame.display.flip()
	for event in pygame.event.get():

		mouse_pos = pygame.mouse.get_pos()
		gain_knob.handle_event(event, mouse_pos)
		dist_knob.handle_event(event, mouse_pos)
		freq_shift_knob.handle_event(event, mouse_pos)
		mute_button.handle_event(event, mouse_pos)
		mic_button.handle_event(event, mouse_pos)
		view_button.handle_event(event, mouse_pos)
		freeze_button.handle_event(event, mouse_pos)
		record_button.handle_event(event, mouse_pos)

		if event.type == pygame.QUIT:
			if record_button.value:
				pygame.display.flip()
				save_file(output_file)
			pygame.quit()
			sys.exit()
		# handle window resize
		if event.type == pygame.VIDEORESIZE: 
			screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
			if event.h < 400 or event.w < 650:
				if event.h < 400: 
					screen = pygame.display.set_mode((event.w, 400), pygame.RESIZABLE)
				if event.w < 650: 
					screen = pygame.display.set_mode((650, event.h), pygame.RESIZABLE)
				if event.h < 400 and event.w < 650: 
					screen = pygame.display.set_mode((650, 400), pygame.RESIZABLE)
			UNIT = min(max(int(event.w/7), 95), 144)
		# handle keybind menu toggle
		elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and mouse_pos[0] > 0 and mouse_pos[0] < 300 and mouse_pos[1] > 0 and mouse_pos[1] < 50:
			if show_keybinds: show_keybinds = False
			else: show_keybinds = True
		elif event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE:
				pygame.quit()
				sys.exit()

# --------------------- CLEANUP --------------------- #
mic_stream.stop_stream()
mic_stream.close()
p.terminate()