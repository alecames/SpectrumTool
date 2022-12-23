# SpectrumTool

## Description

 This application is a spectrum analyzer that displays the frequency spectrum of an audio stream in real-time, with optional effects on the audio stream.

## Features

- Real-time spectrum analyzer
- Toggle between lines and solid spectrum view
- Toggle microphone on/off
- Toggle mute/unmute
- Freeze the spectrum
- Frequency shifter
- Hard clip distortion effect
- Gain control
- Keybind Menu
- Dynamic resizing/rescaling
- Recording to .wav file (will create `out/` folder if it doesn't exist)

## Keybinds & Controls

**Click and drag** a knob to adjust its value or **scroll** with mouse wheel over a knob to adjust its value
Click on a button to toggle its state
- `ESC` to quit
- `V` to toggle between lines and solid spectrum view
- `N` to toggle microphone on/off
- `M` to toggle mute/unmute
- `F` to freeze the spectrum
- `R` to record audio to .wav file
- `SHIFT` + Click to reset a knob to its default value
- `CTRL` + Click to allow finer control of a knob
- Right click on `FREEZE` to toggle freeze mode (other parameters can be adjusted while frozen)
  
---

## Requirements

- [PyAudio](https://pypi.org/project/PyAudio/)
- [Numpy](https://numpy.org)
- [PyGame](https://www.pygame.org/news)

## Usage

  Clone repository and run `py spectrumtool.py`  OR download the `SpectrumTool.v.x.x.exe` executable from the releases section.

## Screenshots

<!-- ## Video [![SpectrumTool Demo](link) -->

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
