# SpectrumTool

## Description

 This application is a spectrum analyzer that displays the frequency spectrum of an audio stream in real-time, with optional effects on the audio stream.

## Features

- Real-time frequency spectrum analyzer
- Solid and line spectrum view
- Microphone on/off toggle
- Output mute/unmute toggle
- Spectrum freezing
- Frequency shifting
- Hard clip distortion effect
- Gain control
- Keybind menu
- Dynamic UI resizing/scaling
- Recording to .wav file (will create `out/` folder if it doesn't exist)

## Keybinds & Controls

**Click and drag** a knob to adjust its value or **scroll** with mouse wheel over a knob to adjust its value. Click on a button to toggle its state.
- `ESC` to quit
- `V` to toggle between lines and solid spectrum view
- `N` to toggle microphone on/off
- `M` to toggle mute/unmute
- `F` to freeze the spectrum
- `R` to record audio to .wav file
- `SHIFT + LEFT CLICK` to reset a knob to its default value
- `CTRL + LEFT CLICK` to allow finer control of a knob
- `RIGHT CLICK` on FREEZE to toggle freeze mode (other parameters can be adjusted while frozen)
  
---

## Requirements

- Microphone/DI input
- [PyAudio](https://pypi.org/project/PyAudio/)
- [Numpy](https://numpy.org)
- [PyGame](https://www.pygame.org/news)
  
*Note: The executable version does not require the Python dependencies, only mic/DI.*

## Usage

  Clone repository and run `py spectrumtool.py` **OR** download the `SpectrumToo.exe` executable from the [Releases](https://github.com/alecames/spectrum-tool/releases/latest) section. The executable is a standalone application and does not require the `assets/` folder or the `out/` folder to be present in the same directory.

## Screenshots

![Audio input](images/Screenshot%202022-12-22%20220225.png)
![Fullscreen](images/Screenshot%202022-12-22%20215729.png)
![Solid spectrum](images/Screenshot%202022-12-22%20220232.png)
![Shifted frozen spectrum](images/Screenshot%202022-12-22%20220250.png)
![Shifted frozen spectrum solid](images/Screenshot%202022-12-22%20220245.png)
![Keybind menu](images/Screenshot%202022-12-22%20220314.png)
![Save message](images/Screenshot%202022-12-22%20220437.png)

<!-- ## Video Demonstration 

[![SpectrumTool Demo](https://i3.ytimg.com/vi/7NLDb_feJFA/maxresdefault.jpg)](https://www.youtube.com/watch?v=7NLDb_feJFA) -->

## License

This project is licensed under the MIT License - See [LICENSE](LICENSE) file for details.
