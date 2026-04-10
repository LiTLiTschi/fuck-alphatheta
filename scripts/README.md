\# Scripts



\## Rekordbox Pixel-BPM Link (v1.0)



A zero-latency BPM detection tool for Rekordbox. It uses OCR to calibrate 5 specific "pixel eyes" on your screen, which then monitor BPM changes using almost 0% CPU.



\### Setup Requirements

1\. \*\*Windows 10/11\*\*: Uses the Win32 API for high-performance transparent overlays.

2\. \*\*Tesseract OCR\*\*: 

&#x20;  - \[Download here](https://github.com/UB-Mannheim/tesseract/wiki).

&#x20;  - Install to `C:\\Program Files\\Tesseract-OCR\\`.

3\. \*\*Python Dependencies\*\*:

&#x20;  ```bash

&#x20;  pip install pytesseract mss pillow numpy opencv-python pywin32

