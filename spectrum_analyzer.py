import pyaudio
import numpy as np
import pygame
import sys
import math
import threading
import scipy.signal as signal
from numba import jit
from pygame import gfxdraw

# visual settings
FPS = 144
FONT_PATH = "./assets/Product Sans Regular.ttf" # font by Google https://befonts.com/product-sans-font.html
TITLE = "Spectrum Analyzer"
FONT_COLOR = (255, 255, 255)
FONT_COLOR_ACCENT = (200, 255, 200)
FONT_SCALE = 1.2
CH_COLOR = (139, 178, 112, 100)
CTRL_BAR_H = 135
CTRL_BAR_COLOR = (34, 36, 30)
TOGGLE_BUTTON_COLOR = (73, 102, 60)
MIC_BUTTON_COLOR = (235, 110, 100)
BUTTON_COLOR = (139, 178, 112)
BUTTON_FREEZE_COLOR = (175, 255, 255)
BUTTON_COLOR_ACCENT = (200, 255, 200)
TIERTIARY_COLOR = (63, 74, 52)
BACKGROUND_COLOR = (27, 27, 27)
SPECTRUM_COLOR = (139, 178, 112)
LINE_COLOR = (255, 255, 255, 12)
CARD_COLOR = (34, 36, 30, 100)

# audio settings
DECAY = 15 # how many frames for the spectrum to decay
RATE = 44100 # sample rate
BUFFER = 1024 # buffer size
RESOLUTION = 44100 # resolution of the spectrum
MIN_FREQ = 20 # min freq to display
MAX_FREQ = RATE / 2 # max freq to display
GAIN_MAX = 5 # max gain

pygame.init()
screen = pygame.display.set_mode((800, 500), pygame.RESIZABLE)
pygame.display.set_caption(TITLE)
icon = pygame.image.load('./assets/icon.png') # icon by Icons8 https://icons8.com
pygame.display.set_icon(icon)
audio_data = np.zeros(1024)

# init audio streams for in and out
p = pyaudio.PyAudio()
mic_stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=BUFFER)
out_stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, output=True, frames_per_buffer=BUFFER)

previous_spectrums = []
gain = 1
fx_toggle = False
view_type_toggle = True
offset = 0
peak_freq = 0
peak_notename = "N/A"
view_btn_color = BUTTON_COLOR
mic_btn_color = MIC_BUTTON_COLOR
mute_btn_color = TOGGLE_BUTTON_COLOR
freeze_btn_color = BUTTON_COLOR
gain_btn_color = BUTTON_COLOR
view_text = "LINE"
freeze = False
mic_toggle = True
mute_toggle = False
show_keybinds = False

font_tiny = pygame.font.Font(FONT_PATH, round(FONT_SCALE* 12))
font_small = pygame.font.Font(FONT_PATH, round(FONT_SCALE* 16))
font_medium = pygame.font.Font(FONT_PATH, round(FONT_SCALE* 20))
font_large = pygame.font.Font(FONT_PATH, round(FONT_SCALE* 28))

note_map = {}
with open("./assets/note.map", "r") as f:
	for line in f:
		line = line.split()
		note_map[int(line[0])] = line[1]

def create_log_scale():
	log_min_freq, log_max_freq = math.log(MIN_FREQ), math.log(MAX_FREQ)
	log_freqs = [log_min_freq + i * (log_max_freq - log_min_freq) / info.current_w for i in range(info.current_w)]
	freqs = [math.exp(f) for f in log_freqs]
	return freqs

def draw_spectrum(screen, previous_spectrums, info, spectrum_h_range, freqs, freqs_tuple):
	y = 0
	for s in previous_spectrums[::-1]:
		points = [(x * info.current_w / len(freqs), y * (value / DECAY) + spectrum_h_range - value) for (x, f), value in zip(freqs_tuple, s)]
		if view_type_toggle:
			gfxdraw.aapolygon(screen, points, SPECTRUM_COLOR)
		else:
			gfxdraw.filled_polygon(screen, points, SPECTRUM_COLOR)
		y += 1

@jit(nopython=True)
def gain_fx(in_data, gain):
	out_data = in_data * gain
	out_data = np.clip(out_data, -32768, 32767)
	return out_data

def filter(in_data, amt):
	out_data = in_data
	b, a = signal.butter(2, 50 / (RATE / 2), 'highpass')
	out_data = signal.filtfilt(b, a, out_data)
	return out_data

while True:
	if not freeze:
		data = mic_stream.read(BUFFER)
		if not mic_toggle:
			data = b'\x00' * BUFFER
	info = pygame.display.Info()
	pygame.time.Clock().tick(FPS)
	screen.fill(BACKGROUND_COLOR)
	title_text = font_large.render(TITLE, True, TIERTIARY_COLOR)
	signature_text = font_tiny.render("by Alec Ames", True, TIERTIARY_COLOR)
	screen.blit(title_text, (FONT_SCALE * 10, FONT_SCALE * 10))
	screen.blit(signature_text, (FONT_SCALE * 12, FONT_SCALE * 42))

	spectrum_h_range = info.current_h - CTRL_BAR_H
	audio_data = np.frombuffer(data, dtype=np.int16)

	audio_data = filter(audio_data, 1)
	audio_data = gain_fx(audio_data, gain)

	spectrum = np.abs(np.fft.rfft(audio_data, n=RESOLUTION))
	dp_spectrum = spectrum
	freqs = create_log_scale()
	
	freqs_tuple = [(x, f) for x, f in enumerate(freqs)]
	dp_spectrum = np.interp(freqs, np.linspace(0, MAX_FREQ, len(dp_spectrum)), dp_spectrum)
	dp_spectrum /= (2 ** 18)
	if np.max(dp_spectrum) > 1:
		dp_spectrum /= np.max(dp_spectrum)
	dp_spectrum *= spectrum_h_range
	dp_spectrum[0], dp_spectrum[-1] = 0, 0  # snaps polygon to bottom of screen
	previous_spectrums.append(dp_spectrum)
	if len(previous_spectrums) > DECAY:
		previous_spectrums.pop(0)

	# write audio data to output stream
	if not mute_toggle:
		out_data = np.int16(audio_data)
		out_data = out_data.tobytes()
		out_stream.write(out_data)
	draw_spectrum(screen, previous_spectrums, info, spectrum_h_range, freqs, freqs_tuple)

	# ----------------- UI ----------------- #

	# fx text
	if mic_toggle: mode_string = "MIC ON"
	else: mode_string = "MIC OFF"
	mode_text = font_medium.render(mode_string, True, FONT_COLOR)
	if mode_text.get_width() + title_text.get_width() + (FONT_SCALE * 20) > info.current_w:
		offset = title_text.get_height() + (FONT_SCALE * 10)
	else:
		offset = 0
	screen.blit(mode_text, (info.current_w - (mode_text.get_width() + (FONT_SCALE * 10)),  (FONT_SCALE * 10) + offset))

	# mouse freq
	mouse_pos = pygame.mouse.get_pos()
	try: 
		if mouse_pos[1] < spectrum_h_range:
			pygame.draw.line(screen, CH_COLOR, (mouse_pos[0], 0), (mouse_pos[0], spectrum_h_range), 1)
			freq_text = font_small.render(f"{int(freqs[mouse_pos[0]])} Hz", True, FONT_COLOR)
			screen.blit(freq_text, (max(mouse_pos[0] - freq_text.get_width() - 15, 0 + (FONT_SCALE * 10)), max(mouse_pos[1] - (FONT_SCALE * 10), FONT_SCALE * 55)))
	except IndexError:
		pass

	# peak freq
	peak_freq_text = font_small.render(f"{int(peak_freq)} Hz", True, FONT_COLOR)
	peak_note_text = font_small.render(f"{peak_notename}", True, FONT_COLOR)
	# if peak freq is above 60hz and above the threshold, display it
	temp_peak_freq = freqs[np.argmax(dp_spectrum)]
	if np.max(dp_spectrum) > 30 and temp_peak_freq > 60: # filter out low freq and low amplitude noise
		peak_freq = temp_peak_freq
		peak_note = int(round(12 * np.log2(peak_freq / 440) + 69))
		if peak_note in note_map:
			peak_notename = note_map[peak_note]
		else:
			peak_notename = "N/A"
		peak_freq_text = font_small.render(f"{int(peak_freq)} Hz", True, FONT_COLOR_ACCENT)
		peak_note_text = font_small.render(f"{peak_notename}", True, FONT_COLOR_ACCENT)
		screen.blit(peak_freq_text, (info.current_w - (peak_freq_text.get_width() + (FONT_SCALE * 10)), (FONT_SCALE * 35) + offset))
		screen.blit(peak_note_text, (info.current_w - (peak_note_text.get_width() + (FONT_SCALE * 10)), (FONT_SCALE * 55) + offset))
	else: 
		screen.blit(peak_freq_text, (info.current_w - (peak_freq_text.get_width() + (FONT_SCALE * 10)), (FONT_SCALE * 35) + offset))
		screen.blit(peak_note_text, (info.current_w - (peak_note_text.get_width() + (FONT_SCALE * 10)), (FONT_SCALE * 55) + offset))

	# keybind popup
	if show_keybinds:
		keybind_title_text = font_medium.render("KEYBINDS", True, FONT_COLOR)
		title_rect = keybind_title_text.get_rect()
		title_rect.center = (info.current_w/2, info.current_h/2 - (FONT_SCALE * info.current_h/3.5))
		screen.blit(keybind_title_text, title_rect)
		subtitle_text = font_tiny.render("Click the title again to close this menu", True, FONT_COLOR)
		subtitle_rect = subtitle_text.get_rect()
		subtitle_rect.center = (info.current_w/2, info.current_h/2 - (FONT_SCALE * info.current_h/3.5) + (FONT_SCALE * 30))
		screen.blit(subtitle_text, subtitle_rect)
		# horizontal line below subtitle
		pygame.draw.line(screen, FONT_COLOR, (info.current_w/2 - (FONT_SCALE * 100), info.current_h/2 - (FONT_SCALE * info.current_h/3.5) + (FONT_SCALE * 45)), (info.current_w/2 + (FONT_SCALE * 100), info.current_h/2 - (FONT_SCALE * info.current_h/3.5) + (FONT_SCALE * 45)), 1)
		keybinds = [
			("View", "V", "Toggle view"),
			("Mute", "M", "Toggle mute"),
			("Mic", "N", "Toggle mic"),
			("Freeze", "F", "Freeze spectrum"),
			("Gain Up", "W", "Increase gain"),
			("Gain Down", "S", "Decrease gain"),
			("Quit", "ESC", "Close the application"),
		]
		for i, keybind in enumerate(keybinds):
			keybind_text = font_tiny.render(f"{keybind[0]} [{keybind[1]}] - {keybind[2]}", True, FONT_COLOR)
			keybind_rect = keybind_text.get_rect()
			keybind_rect.center = (info.current_w/2, info.current_h/2 - (FONT_SCALE * info.current_h/3.5) + (FONT_SCALE * 60) + (FONT_SCALE * 20 * i))
			screen.blit(keybind_text, keybind_rect)

	bar_w = info.current_w
	bar_x = 0
	bar_y = info.current_h - CTRL_BAR_H

	view_btn_x = int(CTRL_BAR_H/2)
	view_btn_y = int((info.current_h - CTRL_BAR_H/2))
	view_btn_r = int(CTRL_BAR_H/3)

	mic_btn_x = int(CTRL_BAR_H/2 + CTRL_BAR_H)
	mic_btn_y = int((info.current_h - CTRL_BAR_H/2))
	mic_btn_r = int(CTRL_BAR_H/3)

	mute_btn_x = int(CTRL_BAR_H/2 + CTRL_BAR_H*2)
	mute_btn_y = int((info.current_h - CTRL_BAR_H/2))
	mute_btn_r = int(CTRL_BAR_H/3)

	gain_btn_x = int(info.current_w - CTRL_BAR_H/2 - CTRL_BAR_H)
	gain_btn_y = int((info.current_h - CTRL_BAR_H/2))
	gain_btn_r = int(CTRL_BAR_H/3)
	gain_btn_angle = int(135 + (gain * 270 / GAIN_MAX))

	freeze_btn_x = int(info.current_w - CTRL_BAR_H/2)
	freeze_btn_y = int(info.current_h - CTRL_BAR_H/2)
	freeze_btn_r = int(CTRL_BAR_H/3)

	gain_text = font_medium.render(f"{int(gain/5*100)}", True, BUTTON_COLOR)
	gain_label_text = font_tiny.render("GAIN", True, TIERTIARY_COLOR)
	view_label_text = font_small.render(view_text, True, view_btn_color)
	mic_label_text = font_small.render("MIC", True, mic_btn_color)
	toggle_label_text = font_small.render("FREEZE", True, freeze_btn_color)
	mute_label_text = font_small.render("MUTE", True, mute_btn_color)

	pygame.draw.rect(screen, CTRL_BAR_COLOR, (bar_x, bar_y, bar_w, CTRL_BAR_H))
	pygame.draw.line(screen, TIERTIARY_COLOR, (0, (info.current_h - CTRL_BAR_H) + 1), (info.current_w + 1, info.current_h - CTRL_BAR_H + 1), 2)

	pygame.gfxdraw.aacircle(screen, view_btn_x, view_btn_y, view_btn_r, view_btn_color)
	pygame.gfxdraw.aacircle(screen, mic_btn_x, mic_btn_y, mic_btn_r, mic_btn_color)
	pygame.gfxdraw.aacircle(screen, freeze_btn_x, freeze_btn_y, freeze_btn_r, freeze_btn_color)
	pygame.gfxdraw.aacircle(screen, mute_btn_x, mute_btn_y, mute_btn_r, mute_btn_color)
	pygame.gfxdraw.arc(screen, gain_btn_x, gain_btn_y, gain_btn_r, 135, 405, TIERTIARY_COLOR)
	pygame.gfxdraw.arc(screen, gain_btn_x, gain_btn_y, gain_btn_r, 135, gain_btn_angle, gain_btn_color)

	# make label for view button
	screen.blit(view_label_text, (view_btn_x - (view_label_text.get_width()/2), view_btn_y - view_label_text.get_height()/2))
	screen.blit(gain_label_text, (gain_btn_x - (gain_label_text.get_width()/2), gain_btn_y + (gain_btn_r * 0.66)))
	screen.blit(gain_text, (gain_btn_x - (gain_text.get_width()/2), gain_btn_y - gain_text.get_height()/2))
	screen.blit(mic_label_text, (mic_btn_x - (mic_label_text.get_width()/2), mic_btn_y - mic_label_text.get_height()/2))
	screen.blit(toggle_label_text, (freeze_btn_x - (toggle_label_text.get_width()/2), freeze_btn_y - toggle_label_text.get_height()/2))
	screen.blit(mute_label_text, (mute_btn_x - (mute_label_text.get_width()/2), mute_btn_y - mute_label_text.get_height()/2))
	gain_btn_color = BUTTON_COLOR

	# ----------------- EVENTS ----------------- #
	# draw each frame
	pygame.display.flip()
	for event in pygame.event.get():
		mouse_pos = pygame.mouse.get_pos()
		if event.type == pygame.QUIT:
			pygame.quit()
			sys.exit()
		# handle window resize
		elif event.type == pygame.VIDEORESIZE: 
			screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
			if event.h < 300 or event.w < 600:
				if event.h < 300: 
					screen = pygame.display.set_mode((event.w, 300), pygame.RESIZABLE)
				if event.w < 600: 
					screen = pygame.display.set_mode((600, event.h), pygame.RESIZABLE)
					CTRL_BAR_H = int(100)
				if event.h < 300 and event.w < 600:
					screen = pygame.display.set_mode((600, 300), pygame.RESIZABLE)
			elif event.h > 900 or event.w > 1400:
				if event.h > 900:
					screen = pygame.display.set_mode((event.w, 900), pygame.RESIZABLE)
				if event.w > 1400:
					screen = pygame.display.set_mode((1400, event.h), pygame.RESIZABLE)
				if event.h > 900 and event.w > 1400:
					screen = pygame.display.set_mode((1400, 900), pygame.RESIZABLE)
			else: CTRL_BAR_H = int(event.w/6)
		# keybind menu
		elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and mouse_pos[0] > 0 and mouse_pos[0] < 300 and mouse_pos[1] > 0 and mouse_pos[1] < 50:
			if show_keybinds:
				show_keybinds = False
			else:
				show_keybinds = True
		# scroll up raise gain
		elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
			if mouse_pos[0] > gain_btn_x - gain_btn_r and mouse_pos[0] < gain_btn_x + gain_btn_r and mouse_pos[1] > gain_btn_y - gain_btn_r and mouse_pos[1] < gain_btn_y + gain_btn_r:
				gain += 0.25
				if gain > GAIN_MAX:
					gain = GAIN_MAX
				gain_btn_color = BUTTON_COLOR_ACCENT
		# scroll down lower gain
		elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
			if mouse_pos[0] > gain_btn_x - gain_btn_r and mouse_pos[0] < gain_btn_x + gain_btn_r and mouse_pos[1] > gain_btn_y - gain_btn_r and mouse_pos[1] < gain_btn_y + gain_btn_r:
				gain -= 0.25
				if gain < 0:
					gain = 0
				gain_btn_color = BUTTON_COLOR_ACCENT
		# handle clicks
		elif event.type == pygame.MOUSEBUTTONDOWN:
			# view button
			if mouse_pos[0] > view_btn_x - view_btn_r and mouse_pos[0] < view_btn_x + view_btn_r and mouse_pos[1] > view_btn_y - view_btn_r and mouse_pos[1] < view_btn_y + view_btn_r:
				view_type_toggle = not view_type_toggle
				view_btn_color = BUTTON_COLOR_ACCENT
				if view_type_toggle:
					view_text = "LINE"
				else:
					view_text = "SOLID"
			# freeze button
			elif mouse_pos[0] > freeze_btn_x - freeze_btn_r and mouse_pos[0] < freeze_btn_x + freeze_btn_r and mouse_pos[1] > freeze_btn_y - freeze_btn_r and mouse_pos[1] < freeze_btn_y + freeze_btn_r:
				freeze = not freeze
				if freeze:
					freeze_btn_color = BUTTON_FREEZE_COLOR
				else:
					freeze_btn_color = BUTTON_COLOR
			# mic button
			elif mouse_pos[0] > mic_btn_x - mic_btn_r and mouse_pos[0] < mic_btn_x + mic_btn_r and mouse_pos[1] > mic_btn_y - mic_btn_r and mouse_pos[1] < mic_btn_y + mic_btn_r:
				mic_toggle = not mic_toggle
				if mic_toggle:
					mic_btn_color = MIC_BUTTON_COLOR
				else:
					mic_btn_color = TOGGLE_BUTTON_COLOR
			# mute button
			elif mouse_pos[0] > mute_btn_x - mute_btn_r and mouse_pos[0] < mute_btn_x + mute_btn_r and mouse_pos[1] > mute_btn_y - mute_btn_r and mouse_pos[1] < mute_btn_y + mute_btn_r:
				mute_toggle = not mute_toggle
				if mute_toggle:
					mute_btn_color = BUTTON_COLOR_ACCENT
				else:
					mute_btn_color = TOGGLE_BUTTON_COLOR
		# freeze toggle on F
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
			freeze = not freeze
			freeze_btn_color = BUTTON_COLOR_ACCENT
		elif event.type == pygame.KEYUP and event.key == pygame.K_f:
			freeze = not freeze
			freeze_btn_color = BUTTON_COLOR
		# mic toggle on M
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_n:
			mic_toggle = not mic_toggle
			if mic_toggle:
				mic_btn_color = MIC_BUTTON_COLOR
			else:
				mic_btn_color = BUTTON_COLOR
		# view toggle on V
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_v:
			view_type_toggle = not view_type_toggle
			view_btn_color = BUTTON_COLOR_ACCENT
			if view_type_toggle:
				view_text = "LINE"
			else:
				view_text = "SOLID"
		# gain up on W
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_w:
			gain += 0.25
			if gain > GAIN_MAX:
				gain = GAIN_MAX
			gain_btn_color = BUTTON_COLOR_ACCENT
		# gain down on S
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_s:
			gain -= 0.25
			if gain < 0:
				gain = 0
			gain_btn_color = BUTTON_COLOR_ACCENT
		# playback toggle on L
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
			mute_toggle = not mute_toggle
			if mute_toggle:
				mute_btn_color = BUTTON_COLOR_ACCENT
			else:
				mute_btn_color = BUTTON_COLOR
		elif event.type == pygame.MOUSEBUTTONUP:
			view_btn_color = BUTTON_COLOR
			freeze_btn_color = BUTTON_COLOR
			freeze = False
		elif event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE:
				pygame.quit()
				sys.exit()
				
mic_stream.stop_stream()
mic_stream.close()
p.terminate()