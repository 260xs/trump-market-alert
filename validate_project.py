# Live Audio Mode

Live audio is the hardest part to do for free without a PC.

This project includes an optional sampler:

```text
.github/workflows/live_audio.yml
```

It uses:

```text
yt-dlp -> public live stream audio URL
ffmpeg -> short audio capture
faster-whisper -> local free transcription
```

Default schedule:

```text
7, 27, 47 minutes every hour
```

Default sample length:

```text
90 seconds
```

Important limitation:

A scheduled GitHub job is not a continuous recorder. If a livestream is 60 minutes and the job samples 90 seconds every 20 minutes, it can miss speech between samples.

Better coverage costs more time:

```text
LIVE_AUDIO_SECONDS=180
```

Strongest free setting that may still work:

```text
LIVE_AUDIO_SECONDS=300
```

But this can be slow and may fail if GitHub delays the job.

True perfect live coverage requires one of these:

```text
PC/server running continuously
paid always-on VPS
paid speech-to-text API
```

Keep the text monitor active even if live audio is enabled. Text sources are faster and more reliable.
