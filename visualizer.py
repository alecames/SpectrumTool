import pyaudio
import numpy as np
import pygame
import sys
import math
from pygame import gfxdraw

# visual settings
FPS = 144
FONT_PATH = "./assets/Product Sans Regular.ttf"
TITLE = "Spectrum Visualizer"
FONT_COLOR = (255, 255, 255)
FONT_COLOR_ACCENT = (139, 178, 112)
FONT_SCALE = 1.2
CH_COLOR = (139, 178, 112, 100)
CTRL_BAR_H = 100
CTRL_BAR_COLOR = (34, 36, 30)
BUTTON_COLOR = (139, 178, 112)
RIDGE_COLOR = (63, 74, 52)
BACKGROUND_COLOR = (27, 27, 27)
SPECTRUM_COLOR = (139, 178, 112)
LINE_COLOR = (255, 255, 255, 12)

# audio settings
DECAY = 15
RATE = 44100
BUFFER = 1024
RESOLUTION = 10000
MIN_FREQ = 20
MAX_FREQ = RATE / 2

pygame.init()
screen = pygame.display.set_mode((600, 400), pygame.RESIZABLE)
pygame.display.set_caption(TITLE)
icon = pygame.image.load('./assets/icon.png')
pygame.display.set_icon(icon)

# init audio streams for in and out
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=BUFFER)
out_stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, output=True, frames_per_buffer=BUFFER)

previous_spectrums = []
gain = 1
fx_toggle = False
view_type_toggle = True
offset = 0
peak_freq = 0
peak_notename = "N/A"

font_tiny = pygame.font.Font(FONT_PATH, round(FONT_SCALE* 12))
font_small = pygame.font.Font(FONT_PATH, round(FONT_SCALE* 16))
font_medium = pygame.font.Font(FONT_PATH, round(FONT_SCALE* 20))
font_large = pygame.font.Font(FONT_PATH, round(FONT_SCALE* 28))

note_map = {}
with open("./assets/note_map.txt", "r") as f:
	for line in f:
		line = line.split()
		note_map[int(line[0])] = line[1]

def create_log_scale():
	log_min_freq, log_max_freq = math.log(MIN_FREQ), math.log(MAX_FREQ)
	log_freqs = [log_min_freq + i * (log_max_freq - log_min_freq) / info.current_w for i in range(info.current_w)]
	freqs = [math.exp(f) for f in log_freqs]
	return freqs

def draw_spectrum(SPECTRUM_COLOR, MAX_LENGTH, screen, previous_spectrums, info, spectrum_h_range, freqs, freqs_tuple):
	y = 0
	for s in previous_spectrums[::-1]:
		points = [(x * info.current_w / len(freqs), y * (value / MAX_LENGTH) + spectrum_h_range - value) for (x, f), value in zip(freqs_tuple, s)]
		if view_type_toggle:
			gfxdraw.aapolygon(screen, points, SPECTRUM_COLOR)
		else:
			gfxdraw.filled_polygon(screen, points, SPECTRUM_COLOR)
		y += 1

def effect(gain, fx_data): 
	
	return fx_data

while True:
	data = stream.read(BUFFER)
	info = pygame.display.Info()
	pygame.time.Clock().tick(FPS)
	screen.fill(BACKGROUND_COLOR)
	title_text = font_large.render(TITLE, True, RIDGE_COLOR)
	signature_text = font_tiny.render("by Alec Ames", True, RIDGE_COLOR)
	screen.blit(title_text, (FONT_SCALE * 10, FONT_SCALE * 10))
	screen.blit(signature_text, (FONT_SCALE * 12, FONT_SCALE * 42))

	spectrum_h_range = info.current_h - CTRL_BAR_H

	audio_data = np.frombuffer(data, dtype=np.int16)

	if fx_toggle:
		audio_data_effect = effect(gain, audio_data)
		audio_data = audio_data_effect
	
	spectrum = np.abs(np.fft.rfft(audio_data, n=RESOLUTION))
	dp_spectrum = spectrum
	freqs = create_log_scale()
	
	freqs_tuple = [(x, f) for x, f in enumerate(freqs)]
	dp_spectrum = np.interp(freqs, np.linspace(0, MAX_FREQ, len(dp_spectrum)), dp_spectrum)
	dp_spectrum /= (2 ** 20)
	if np.max(dp_spectrum) > 1:
		dp_spectrum /= np.max(dp_spectrum)
	dp_spectrum *= spectrum_h_range
	dp_spectrum[0], dp_spectrum[-1] = 0, 0  # snaps polygon to bottom of screen
	previous_spectrums.append(dp_spectrum)
	if len(previous_spectrums) > DECAY:
		previous_spectrums.pop(0)

	# write audio data to output stream
	out_data = np.int16(audio_data)
	out_data = out_data.tobytes()
	out_stream.write(out_data)
	draw_spectrum(SPECTRUM_COLOR, DECAY, screen, previous_spectrums, info, spectrum_h_range, freqs, freqs_tuple)

	# ----------------- UI ----------------- #

	# fx text
	if fx_toggle: mode_string = "Effect ON"
	else: mode_string = "Effect OFF"
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
	if np.max(dp_spectrum) > 20:
		peak_freq = freqs[np.argmax(dp_spectrum)]
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

	bar_width = info.current_w
	bar_x = 0
	bar_y = info.current_h - CTRL_BAR_H

	button_x = int(CTRL_BAR_H/2)
	button_y = int((info.current_h - CTRL_BAR_H/2))
	button_radius = 25

	knob_x = int(info.current_w - CTRL_BAR_H/2)
	knob_y = int(info.current_h - CTRL_BAR_H/2)
	knob_radius = 25

	pygame.draw.rect(screen, CTRL_BAR_COLOR, (bar_x, bar_y, bar_width, CTRL_BAR_H))
	pygame.draw.line(screen, RIDGE_COLOR, (0, (info.current_h - CTRL_BAR_H) + 3), (info.current_w + 1, info.current_h - CTRL_BAR_H + 3), 5)
	pygame.gfxdraw.aacircle(screen, button_x, button_y, button_radius, BUTTON_COLOR)
	pygame.gfxdraw.aacircle(screen, knob_x, knob_y, knob_radius, BUTTON_COLOR)

	# ----------------- EVENTS ----------------- #
	# draw each frame
	pygame.display.flip()
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			pygame.quit()
			sys.exit()
		elif event.type == pygame.VIDEORESIZE:
			screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
		elif event.type == pygame.MOUSEBUTTONDOWN:
			mouse_x, mouse_y = pygame.mouse.get_pos()
			if mouse_x > button_x - button_radius and mouse_x < button_x + button_radius and mouse_y > button_y - button_radius and mouse_y < button_y + button_radius:
				view_type_toggle = not view_type_toggle
		elif event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE:
				pygame.quit()
				sys.exit()
				
stream.stop_stream()
stream.close()
p.terminate()