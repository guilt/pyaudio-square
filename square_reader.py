#!/usr/bin/env python
# pylint: disable=C0111,R1708

"""
square_reader.py
"""
from __future__ import print_function

import audioop
import sys
from collections import deque

import pyaudio

CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5

THRESHOLD_FACTOR = 3.5
FIRST_PEAK_FACTOR = 0.8
SECOND_PEAK_FACTOR = 0.5


def __get_chunk(src, bias):
    audio_data = src.read(10000)
    data = audioop.bias(audio_data, 2, bias)
    return data, audioop.maxpp(data, 2)


def get_swipe():
    audio = pyaudio.PyAudio()

    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

    baselines = deque([2 ** 15] * 4)
    bias = 0
    old_data = b''

    while True:

        data, power = __get_chunk(stream, bias)

        baseline = sum(baselines) / len(baselines) * THRESHOLD_FACTOR
        print(power, baseline, power / (baseline or 1))

        chunks = []
        while power > baseline:
            print(power, baseline, power / (baseline or 1), '*')
            chunks.append(data)
            data, power = __get_chunk(stream, bias)

        if len(chunks) > 1:
            data = old_data + b''.join(chunks) + data
            while audioop.maxpp(data[:3000], 2) < baseline / 2:
                data = data[1000:]
            while audioop.maxpp(data[-3000:], 2) < baseline / 2:
                data = data[:-1000]

            return audioop.bias(data, 2, -audioop.avg(data, 2))

        old_data = data

        bias = -audioop.avg(data, 2)

        baselines.popleft()
        baselines.append(power)


def get_samples(data, width=2):
    return list(audioop.getsample(data, width, i) for i in range(len(data) // width))


def get_peaks(data):
    peak_threshold = audioop.maxpp(data[:1000], 2) * FIRST_PEAK_FACTOR

    samples = get_samples(data)
    if not samples:
        return

    i = 0
    old_i = 0
    sign = 1

    while i < len(samples):
        peak = 0
        while samples[i] * sign > peak_threshold:
            peak = max(samples[i] * sign, peak)
            i += 1

        if peak:
            if old_i:
                yield i - old_i
            old_i = i
            sign *= -1
            peak_threshold = peak * SECOND_PEAK_FACTOR

        i += 1


def get_bits(peaks):
    peaks = list(peaks)

    # Discard first 5 peaks
    peaks = peaks[5:]

    # Clock next 4 peaks (should be zeros)
    clocks = deque([p / 2.0 for p in peaks[:4]])

    i = 0
    while i < len(peaks) - 2:
        peak = peaks[i]

        if peak > 1.5 * sum(clocks, 0.0) / len(clocks):
            yield 0
            i += 1
            clocks.append(peak / 2)
        else:
            yield 1
            i += 2
            clocks.append(peak)
        clocks.popleft()


def get_bytes(bits, width=5):
    bits = list(bits)

    if not bits:
        return

    # Discard leading 0s
    while bits[0] == 0:
        bits = bits[1:]

    while 1:
        byte, bits = bits[:width], bits[width:]
        if len(byte) < width or sum(byte) % 2 != 1:
            return
        yield byte


def bcd_chr(byte):
    return chr(int(''.join(map(str, byte[-2::-1])), 2) + 48)


def get_bcd_chars(_bytes):
    _bytes = list(_bytes)

    if bcd_chr(_bytes[0]) != ';':
        # Try reversed
        _bytes = [byte[::-1] for byte in reversed(_bytes)]

    ibytes = iter(_bytes)
    start = next(ibytes)

    if bcd_chr(start) != ';':
        raise DecodeError('No Start Sentinel')

    lrc = start
    try:
        while True:
            byte = next(ibytes)
            char = bcd_chr(byte)

            for i in range(len(lrc) - 1):
                lrc[i] = (lrc[i] + byte[i]) % 2

            if char == '?':
                lrc[-1] = sum(lrc[:-1], 1) % 2
                real_lrc = next(ibytes)
                if real_lrc != lrc:
                    raise DecodeError('Bad LRC')
                return

            yield char

    except StopIteration:
        raise DecodeError('No End Sentinel')


class DecodeError(Exception):
    pass


def main():
    try:
        data = get_swipe()
        peaks = list(get_peaks(data))
        bits = list(get_bits(peaks))
        _bytes = list(get_bytes(bits))
        chars = get_bcd_chars(_bytes)
        print(''.join(chars))
    except DecodeError as decode_error:
        print(decode_error, file=sys.stderr)


if __name__ == '__main__':
    main()
