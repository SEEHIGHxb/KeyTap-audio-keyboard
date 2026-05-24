========================================================================
                      AUDIO KEYBOARD APPLICATION
                       * Cyber Obsidian Edition *
========================================================================

An interactive, system-wide keypress audio feedback utility. 
Plays high-fidelity mechanical switches or retro-arcade chime sound 
effects instantly when you press ANY key on your keyboard!

Created by Jojo & Antigravity Coding Assistant (DeepMind)

------------------------------------------------------------------------
👉 QUICK START GUIDE (For General Users)
------------------------------------------------------------------------

1. UNZIP the folder.
2. Double-click the "AudioKeyboard.exe" file.
3. Open any text editor, web browser, or game, and start typing! 
   You will instantly hear satisfying sound effects matching your keypresses.

------------------------------------------------------------------------
✨ KEY FEATURES IN THE DASHBOARD
------------------------------------------------------------------------

* MASTER AUDIO TOGGLE:
  A sleek toggle switch labeled "Enable Sound Playback". When switched OFF,
  the app runs silently in the background, counting your keystrokes without
  making noise or affecting typing.

* MASTER VOLUME CONTROL:
  Slide the volume bar to adjust sound effect levels to your preference.

* SOUND PACK SELECTOR:
  A dropdown ComboBox lets you swap between different acoustics in real-time.
  
* VISUAL CONSOLE LOG:
  A terminal-style window scrolling live with keypress details and system logs!

* REAL-TIME LED INDICATOR:
  A glowing visual light that pulses (Cyan for ACTIVE, Crimson for MUTED)
  so you always know the app's status at a glance.

------------------------------------------------------------------------
🚀 ZERO-CONFIGURATION RUN (Offline Synthesizer)
------------------------------------------------------------------------

When you open this app for the first time on a new computer:
It will detect that there are no audio files, and automatically synthesize
two beautifully textured sound packs from scratch inside the "sound_packs" 
folder:
1. "Mechanical_Clicks" (Cherry Blue, Cherry Brown, Cherry Black, Spacebar Thock, Stabilizer Rattle)
2. "Retro_Arcade" (Laser Zap, Coin Pickup, Powerup Rise, Bubble Pop, Alert)

------------------------------------------------------------------------
🎵 HOW TO ADD YOUR OWN CUSTOM SOUND PACKS!
------------------------------------------------------------------------

Want to use anime sounds, meme clips, or custom typing sounds? It's easy!

1. Open the "sound_packs" folder right next to "AudioKeyboard.exe".
2. Create a new folder (e.g., "Meme_Sounds").
3. Drop your favourite .wav, .mp3, or .ogg sound files in that folder.
4. Open the Audio Keyboard dashboard, click the refresh button (🔄) next
   to the dropdown, and select your new pack!

*Pro-Tip for Custom Packs:*
If your custom pack has generic numbered files (like voice_1.wav to voice_20.wav),
the app will automatically route them:
- Spacebar: plays clips near the end (pauses).
- Enter: plays transitional clips.
- Backspace: plays deletion clips.
- Normal typing: cycles through standard character clips.

------------------------------------------------------------------------
💻 SYSTEM COMPATIBILITY & PERFORMANCE
------------------------------------------------------------------------

* Zero Input Lag: Runs global hooks on a dedicated background thread,
  ensuring your typing speed is 100% unaffected.
* Low Memory Latency: Pygame loads sounds directly to RAM, allowing overlapping
  sounds to play polyphonically without stuttering.
* Clean Exit: Closing the GUI automatically terminates all keyboard hooks
  and audio mixers, leaving your system completely clean.

Enjoy typing!
========================================================================
