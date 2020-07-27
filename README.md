# PyAudio Square Reader

It was ported by me to a working *pyaudio* port, and test with help from volunteers. Thank you!
It will help you read Credit Cards yourself.

# Install Requirements

```bash
pip install -r requirements.txt
```
# Running

Connect the Square Card reader to your audio input. When running in a terminal it
may be easier to run in a loop until it reads the card. When testing, the older
Square Card reader worked more often than the newer version.

```bash
    while true; do
        ./square_reader.py && break
    done
```
# Feedback

Please feel free to send patches if you wish to improve this. Thanks!
