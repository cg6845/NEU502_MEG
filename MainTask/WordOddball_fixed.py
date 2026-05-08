#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual Word Oddball - MEG Experiment, EyeLink, with Blink Trials
=================================================================
Purpose: OPM MEG data collection
         (ERF averaging, time-frequency decomposition, source localization)

Paradigm Details (adapted from FieldTrip oddball tutorial):
    - Standard stimulus: imageable word (e.g., table, horse, lamp)
    - Deviant stimulus:  non-imageable word (e.g., justice, courage)
    - Each word displayed for 500 ms (white text on black background)
    - Deviant appears after every 3-7 standards (randomized)
    - ISI: 700-900 ms uniform jitter (offset to onset)
    - Passive reading with fixation cross during ISI
    - Blink trial (green fixation cross) after each deviant

Word Lists:
    - Loaded from word_lists.csv (must be in same directory)
    - 200 imageable (concrete) words
    - 200 non-imageable (abstract) words
    - Words sampled randomly from pools (recycled with shuffle)

Trigger Scheme (VPIXX Pixel Mode Blue):
    - 1x1 pixel patch, upper-left corner
    - Standard (trigger 1): RGB = (0, 0, 1)
    - Deviant  (trigger 2): RGB = (0, 0, 2)
    - Blink    (trigger 4): RGB = (0, 0, 4)
    - Reset    (trigger 0): RGB = (0, 0, 0)

Blink Trials:
    - Fixation cross turns green after each deviant trial
    - Subject blinks freely during this period
    - Keeps blink artifacts away from the ERP window
    - No stimulus or trigger during blink trials

Eye Tracker:
    - SR Research EyeLink via pylink
    - Continuous recording throughout experiment
    - Event messages: standard, deviant, blink
    - EDF file downloaded at end of session

Output:
    - CSV log: TRIALID, Condition, Word, onset_time, ISI
    - EDF file: eye tracking data with event messages
"""

import numpy as np
from psychopy import visual, core, event, gui, data, monitors
from psychopy import logging
import os
import sys
import csv
import platform
try:
    import pylink
    from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
    EYELINK_AVAILABLE = hasattr(pylink, "EyeLinkCustomDisplay")
except Exception:
    pylink = None
    EyeLinkCoreGraphicsPsychoPy = None
    EYELINK_AVAILABLE = False

# Show only critical log messages in the PsychoPy console
logging.console.setLevel(logging.CRITICAL)

# Switch to the script folder
script_path = os.path.dirname(sys.argv[0])
if len(script_path) != 0:
    os.chdir(script_path)

# =============================================================================
# EXPERIMENT PARAMETERS
# =============================================================================

# Word display
WORD_DURATION = 0.500      # seconds - how long each word is shown
WORD_HEIGHT = 60           # pixels - text height for word stimuli

# Trial structure - gap-based (FieldTrip style)
# A deviant appears after every MIN_GAP to MAX_GAP standards
N_TOTAL = 800              # total stimulus trials (~20 min with blinks)
N_INITIAL_STANDARDS = 10   # standards before first deviant
MIN_GAP = 3                # min standards between deviants
MAX_GAP = 7                # max standards between deviants

# Timing
ISI_MIN = 0.700            # seconds (offset to onset)
ISI_MAX = 0.900            # seconds

# Blink trials
BLINK_DURATION = 1.500     # seconds - green fixation cross after deviants
BLINK_COLOR = 'green'      # fixation cross color during blink cue

# Display colors (black background, white text)
# FIXED: inverted from white background / black text — dark background keeps
#        the pupil dilated for more reliable EyeLink tracking
BG_COLOR = [0, 0, 0]           # black background (RGB 0-255)
TEXT_COLOR = 'white'           # word color
FIX_COLOR = 'white'            # fixation cross color

# Trigger pixel (VPIXX Pixel Mode Blue)
TRIGGER_SIZE = 1          # pixels
TRIGGER_STANDARD = [0, 0, 1]    # RGB 0-255
TRIGGER_DEVIANT = [0, 0, 2]     # RGB 0-255
TRIGGER_BLINK = [0, 0, 4]       # RGB 0-255
TRIGGER_RESET = [0, 0, 0]       # RGB 0-255

# Word list file
WORD_LIST_FILE = 'word_lists.csv'

# EyeLink settings
DUMMY_MODE = False         # set True to test without tracker connected

# =============================================================================
# FUNCTIONS
# =============================================================================

def load_word_lists(filepath):
    """Load standard and deviant word pools from CSV file.

    Parameters
    ----------
    filepath : str
        Path to CSV file with columns: word, category, imageability.
        category should be 'standard' (imageable) or 'deviant'
        (non-imageable).

    Returns
    -------
    standard_words : list of str
        Pool of imageable (standard) words.
    deviant_words : list of str
        Pool of non-imageable (deviant) words.
    """
    standard_words = []
    deviant_words = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row['word'].strip()
            cat = row['category'].strip().lower()
            if cat == 'standard':
                standard_words.append(word)
            elif cat == 'deviant':
                deviant_words.append(word)

    if len(standard_words) == 0 or len(deviant_words) == 0:
        raise ValueError("Word list must contain both standard and deviant "
                         "words. Check your CSV file.")

    return standard_words, deviant_words


def generate_trial_sequence(n_total, n_initial, min_gap, max_gap):
    """Generate trial sequence using gap-range approach.

    Each deviant appears after a random number of standards drawn
    uniformly from [min_gap, max_gap]. The sequence is built until
    n_total trials are reached.

    Parameters
    ----------
    n_total : int
        Total number of trials.
    n_initial : int
        Number of initial standard trials.
    min_gap : int
        Minimum standards before each deviant.
    max_gap : int
        Maximum standards before each deviant.

    Returns
    -------
    sequence : list of str
        List of 'standard' or 'deviant' for each trial.
    """
    rng = np.random.default_rng()
    sequence = ['standard'] * n_initial

    while len(sequence) < n_total:
        # Random number of standards before next deviant
        gap = rng.integers(min_gap, max_gap + 1)

        # Add standards
        for _ in range(gap):
            if len(sequence) >= n_total:
                break
            sequence.append('standard')

        # Add deviant (if room)
        if len(sequence) < n_total:
            sequence.append('deviant')

    # Trim to exact length
    sequence = sequence[:n_total]

    # Ensure the sequence does not end on a deviant
    if sequence[-1] == 'deviant':
        sequence[-1] = 'standard'

    return sequence


def assign_words(trial_sequence, standard_pool, deviant_pool):
    """Assign a word to each trial from the appropriate pool.

    Words are sampled randomly. If the pool is smaller than the number
    of trials for that condition, words are reused (cycled with shuffle).

    Parameters
    ----------
    trial_sequence : list of str
        List of 'standard' or 'deviant' for each trial.
    standard_pool : list of str
        Pool of imageable (standard) words.
    deviant_pool : list of str
        Pool of non-imageable (deviant) words.

    Returns
    -------
    word_sequence : list of str
        A word for each trial.
    """
    rng = np.random.default_rng()

    n_standards = trial_sequence.count('standard')
    n_deviants = trial_sequence.count('deviant')

    # Create shuffled word sequences with recycling
    std_words = list(standard_pool)
    rng.shuffle(std_words)
    while len(std_words) < n_standards:
        extra = list(standard_pool)
        rng.shuffle(extra)
        std_words.extend(extra)
    std_words = std_words[:n_standards]

    dev_words = list(deviant_pool)
    rng.shuffle(dev_words)
    while len(dev_words) < n_deviants:
        extra = list(deviant_pool)
        rng.shuffle(extra)
        dev_words.extend(extra)
    dev_words = dev_words[:n_deviants]

    # Assign words to trials
    word_sequence = []
    std_idx = 0
    dev_idx = 0
    for cond in trial_sequence:
        if cond == 'standard':
            word_sequence.append(std_words[std_idx])
            std_idx += 1
        else:
            word_sequence.append(dev_words[dev_idx])
            dev_idx += 1

    return word_sequence


def rgb_255_to_psychopy(rgb):
    """Convert RGB [0-255] to PsychoPy color space [-1, 1].

    Parameters
    ----------
    rgb : list
        [R, G, B] values in 0-255 range.

    Returns
    -------
    list
        [R, G, B] values in -1 to 1 range.
    """
    return [(c / 127.5) - 1.0 for c in rgb]


def terminate_task(win, el_tracker, edf_file, session_folder,
                   local_edf_name):
    """Gracefully shut down: stop recording, download EDF, close window.

    Parameters
    ----------
    win : visual.Window
        PsychoPy window.
    el_tracker : pylink.EyeLink or None
        EyeLink tracker object (None if EyeLink unavailable).
    edf_file : str
        EDF filename on the Host PC.
    session_folder : str
        Local folder to save the EDF file.
    local_edf_name : str
        Full-length local EDF filename (without extension).
    """
    if EYELINK_AVAILABLE and el_tracker is not None and el_tracker.isConnected():
        # Stop recording if active
        error = el_tracker.isRecording()
        if error == pylink.TRIAL_OK:
            pylink.pumpDelay(100)
            el_tracker.stopRecording()

        # Put tracker in offline mode
        el_tracker.setOfflineMode()
        el_tracker.sendCommand('clear_screen 0')
        pylink.msecDelay(500)

        # Close the EDF file on the Host PC
        el_tracker.closeDataFile()

        # Download the EDF file
        msg = visual.TextStim(win,
                              text='EDF data is transferring from '
                                   'EyeLink Host PC...',
                              color='white', height=30)
        msg.draw()
        win.flip()

        local_edf = os.path.join(session_folder,
                                 local_edf_name + '.EDF')
        try:
            el_tracker.receiveDataFile(edf_file, local_edf)
            print(f"EDF saved to: {local_edf}")
        except RuntimeError as error:
            print(f"ERROR downloading EDF: {error}")

        # Close the link
        el_tracker.close()

    win.close()
    core.quit()
    sys.exit()


# =============================================================================
# PARTICIPANT INFO DIALOG
# =============================================================================

exp_info = {'participant': '', 'session': '001'}
dlg = gui.DlgFromDict(dictionary=exp_info, title='Visual Word Oddball',
                       order=['participant', 'session'])
if not dlg.OK:
    core.quit()

exp_info['date'] = data.getDateStr()

# =============================================================================
# LOAD WORD LISTS
# =============================================================================
# FIXED: moved to after participant dialog so a missing CSV crashes with a
#        clear error message rather than before the participant ID is entered

standard_pool, deviant_pool = load_word_lists(WORD_LIST_FILE)
print(f"Loaded {len(standard_pool)} standard (imageable) words")
print(f"Loaded {len(deviant_pool)} deviant (non-imageable) words")

# Output directories - CSV log and EDF go to the same session folder
results_folder = 'results'
os.makedirs(results_folder, exist_ok=True)

# EDF filename: short version for Host PC (max 8 chars),
# full version for local download
sub = exp_info['participant'].replace('-', '').replace('_', '')
ses = exp_info['session'].replace('-', '').replace('_', '')
edf_fname = f"s{sub}s{ses}"[:8]    # e.g., "s001s01" - truncate to 8 chars
local_edf_name = (f"sub-{exp_info['participant']}"
                  f"_ses-{exp_info['session']}_task-wordoddball")

# Session folder for all outputs (EDF + CSV)
session_folder = os.path.join(results_folder, local_edf_name)
os.makedirs(session_folder, exist_ok=True)

# CSV log filename (same folder as EDF)
filename = os.path.join(session_folder, local_edf_name)

# =============================================================================
# EYELINK: CONNECT AND CONFIGURE
# =============================================================================

el_tracker = None
edf_file = edf_fname + ".EDF"

if EYELINK_AVAILABLE:
    # Step 1: Connect to the EyeLink Host PC
    if DUMMY_MODE:
        el_tracker = pylink.EyeLink(None)
    else:
        try:
            el_tracker = pylink.EyeLink("100.1.1.1")
        except RuntimeError as error:
            print(f"ERROR: {error}")
            core.quit()
            sys.exit()

    # Step 2: Open an EDF data file on the Host PC
    try:
        el_tracker.openDataFile(edf_file)
    except RuntimeError as err:
        print(f"ERROR: {err}")
        if el_tracker.isConnected():
            el_tracker.close()
        core.quit()
        sys.exit()

    # Add a header to the EDF file
    preamble_text = 'RECORDED BY %s' % os.path.basename(__file__)
    el_tracker.sendCommand("add_file_preamble_text '%s'" % preamble_text)

    # Step 3: Configure the tracker
    el_tracker.setOfflineMode()

    # Get tracker version
    eyelink_ver = 0
    if not DUMMY_MODE:
        vstr = el_tracker.getTrackerVersionString()
        eyelink_ver = int(vstr.split()[-1].split('.')[0])
        print(f"Running experiment on {vstr}, version {eyelink_ver}")

    # File and Link data control
    file_event_flags = ('LEFT,RIGHT,FIXATION,SACCADE,BLINK,'
                        'MESSAGE,BUTTON,INPUT')
    link_event_flags = ('LEFT,RIGHT,FIXATION,SACCADE,BLINK,'
                        'BUTTON,FIXUPDATE,INPUT')
    if eyelink_ver > 3:
        file_sample_flags = ('LEFT,RIGHT,GAZE,HREF,RAW,AREA,HTARGET,'
                             'GAZERES,BUTTON,STATUS,INPUT')
        link_sample_flags = ('LEFT,RIGHT,GAZE,GAZERES,AREA,HTARGET,'
                             'STATUS,INPUT')
    else:
        file_sample_flags = ('LEFT,RIGHT,GAZE,HREF,RAW,AREA,'
                             'GAZERES,BUTTON,STATUS,INPUT')
        link_sample_flags = ('LEFT,RIGHT,GAZE,GAZERES,AREA,'
                             'STATUS,INPUT')

    el_tracker.sendCommand("file_event_filter = %s" % file_event_flags)
    el_tracker.sendCommand("file_sample_data = %s" % file_sample_flags)
    el_tracker.sendCommand("link_event_filter = %s" % link_event_flags)
    el_tracker.sendCommand("link_sample_data = %s" % link_sample_flags)

    # Calibration type
    el_tracker.sendCommand("calibration_type = HV9")
else:
    print("EyeLink not available - running without eye tracking.")

# =============================================================================
# SETUP WINDOW AND STIMULI
# =============================================================================

# Window - black background
win = visual.Window(
    fullscr=True,
    color=BG_COLOR,
    colorSpace='rgb255',
    units='pix',
    allowGUI=False,
    screen=0               # change if projector is on a different display
)

# Get window dimensions
win_w, win_h = win.size
scn_width = int(win_w)
scn_height = int(win_h)

# Send display coordinates to the tracker
if EYELINK_AVAILABLE and el_tracker is not None:
    el_coords = "screen_pixel_coords = 0 0 %d %d" % (scn_width - 1,
                                                        scn_height - 1)
    el_tracker.sendCommand(el_coords)
    dv_coords = "DISPLAY_COORDS  0 0 %d %d" % (scn_width - 1, scn_height - 1)
    el_tracker.sendMessage(dv_coords)

# =============================================================================
# EYELINK: CALIBRATION GRAPHICS
# =============================================================================

if EYELINK_AVAILABLE and el_tracker is not None:
    # Configure the graphics environment for calibration
    genv = EyeLinkCoreGraphicsPsychoPy(el_tracker, win)

    # Calibration colors: white target on black background
    # FIXED: was black target on white background — now matches experiment display
    foreground_color = (1, 1, 1)
    background_color = (-1, -1, -1)
    genv.setCalibrationColors(foreground_color, background_color)

    # Calibration target type
    genv.setTargetType('circle')
    genv.setTargetSize(24)

    # Calibration sounds
    genv.setCalibrationSounds('', '', '')

    # Request Pylink to use our PsychoPy window for calibration
    pylink.openGraphicsEx(genv)

# Fixation cross (white on black)
fixation = visual.ShapeStim(
    win,
    vertices=((0, -15), (0, 15), (0, 0), (-15, 0), (15, 0)),
    lineWidth=3,
    closeShape=False,
    lineColor=FIX_COLOR,
    colorSpace='named'
)

# Blink cue fixation cross (green) - same shape, different color
fixation_blink = visual.ShapeStim(
    win,
    vertices=((0, -15), (0, 15), (0, 0), (-15, 0), (15, 0)),
    lineWidth=3,
    closeShape=False,
    lineColor=BLINK_COLOR,
    colorSpace='named'
)

# Word stimulus (white text on black background)
word_stim = visual.TextStim(
    win,
    text='',
    color=TEXT_COLOR,
    height=WORD_HEIGHT,
    font='Arial',
    wrapWidth=None
)

# Trigger pixel - 1x1 pixel in upper-left corner
trigger_x = -win_w / 2.0 + TRIGGER_SIZE / 2.0
trigger_y = win_h / 2.0 - TRIGGER_SIZE / 2.0

trigger_patch = visual.Rect(
    win,
    width=TRIGGER_SIZE,
    height=TRIGGER_SIZE,
    pos=(trigger_x, trigger_y),
    lineWidth=0,
    fillColor=rgb_255_to_psychopy(TRIGGER_RESET),
    fillColorSpace='rgb',
    lineColor=rgb_255_to_psychopy(TRIGGER_RESET),
    lineColorSpace='rgb'
)

# =============================================================================
# GENERATE TRIAL SEQUENCE AND ASSIGN WORDS
# =============================================================================

trial_sequence = generate_trial_sequence(
    N_TOTAL, N_INITIAL_STANDARDS, MIN_GAP, MAX_GAP
)

word_sequence = assign_words(trial_sequence, standard_pool, deviant_pool)

n_deviants = trial_sequence.count('deviant')
n_standards = trial_sequence.count('standard')
est_stim_time = N_TOTAL * (WORD_DURATION + (ISI_MIN + ISI_MAX) / 2.0)
est_blink_time = n_deviants * BLINK_DURATION
est_duration = (est_stim_time + est_blink_time) / 60.0
print(f"Sequence: {n_standards} standards, {n_deviants} deviants "
      f"({n_deviants/N_TOTAL*100:.1f}%)")
print(f"Blink trials: {n_deviants} (after each deviant)")
print(f"Estimated run time: {est_duration:.1f} minutes")

# Pre-generate all ISIs
rng = np.random.default_rng()
isis = rng.uniform(ISI_MIN, ISI_MAX, size=N_TOTAL)

# =============================================================================
# EYELINK: CALIBRATE
# =============================================================================

if EYELINK_AVAILABLE and el_tracker is not None:
    # Show calibration instructions
    cal_msg = visual.TextStim(
        win,
        text=(
            "Before we begin the experiment, we need to\n"
            "calibrate the eye tracker.\n\n"
            "A dot will appear at various locations on the screen.\n"
            "Simply follow the dot with your eyes. Do not anticipate\n"
            "where it will move - wait for it to appear in its new\n"
            "location before looking there.\n\n"
            "We may need to repeat the calibration, so please\n"
            "be patient.\n\n"
            "Experimenter: Press ENTER to begin calibration."
        ),
        color='white',
        height=30,
        wrapWidth=800
    )
    cal_msg.draw()
    win.flip()
    event.waitKeys(keyList=['return'])

    # Run calibration (skip in Dummy Mode)
    if not DUMMY_MODE:
        try:
            el_tracker.doTrackerSetup()
        except RuntimeError as err:
            print(f"ERROR: {err}")
            el_tracker.exitCalibration()

# =============================================================================
# EYELINK: DRIFT CHECK & START RECORDING
# =============================================================================

if EYELINK_AVAILABLE and el_tracker is not None:
    # Drift check at fixation (center of screen)
    while not DUMMY_MODE:
        if (not el_tracker.isConnected()) or el_tracker.breakPressed():
            terminate_task(win, el_tracker, edf_file, session_folder,
                           local_edf_name)
        try:
            error = el_tracker.doDriftCorrect(int(scn_width / 2.0),
                                               int(scn_height / 2.0), 1, 1)
            if error is not pylink.ESC_KEY:
                break
        except Exception:
            pass

    # Put tracker in offline mode before starting recording
    el_tracker.setOfflineMode()

    # Start continuous recording for the entire experiment
    try:
        el_tracker.startRecording(1, 1, 1, 1)
    except RuntimeError as error:
        print(f"ERROR: {error}")
        terminate_task(win, el_tracker, edf_file, session_folder,
                       local_edf_name)

    # Allow the tracker to cache some samples
    pylink.pumpDelay(100)

    # Mark the start of the experiment in the EDF
    el_tracker.sendMessage('EXPERIMENT_START')

# =============================================================================
# PRE-EXPERIMENT INSTRUCTIONS
# =============================================================================

# Show task instructions before starting trials
instructions = visual.TextStim(
    win,
    text=(
        "You will see a series of words on the screen.\n"
        "Please read each word silently and keep your\n"
        "eyes on the center of the screen.\n\n"
        "When the fixation cross turns green, please blink.\n"
        "Otherwise, try not to blink.\n\n"
        "Stay still and relaxed.\n\n"
        "Experimenter: Press SPACE to begin experiment."
    ),
    color='white',
    height=30,
    wrapWidth=800
)
instructions.draw()
win.flip()
event.waitKeys(keyList=['space'])

# Brief pause before starting
fixation.draw()
trigger_patch.fillColor = rgb_255_to_psychopy(TRIGGER_RESET)
trigger_patch.draw()
win.flip()
core.wait(2.0)

# =============================================================================
# MAIN EXPERIMENT LOOP
# =============================================================================

# FIXED: removed unused clock = core.Clock() — onset times come from win.flip()
trial_log = []

for trial_num in range(N_TOTAL):

    # Check for escape key
    if event.getKeys(keyList=['escape']):
        if EYELINK_AVAILABLE and el_tracker is not None:
            el_tracker.sendMessage('EXPERIMENT_ABORTED trial %d' % (trial_num + 1))
        break

    # Check tracker connection
    if EYELINK_AVAILABLE and el_tracker is not None and not DUMMY_MODE:
        if (not el_tracker.isConnected()) or el_tracker.breakPressed():
            break

    # Determine condition and word
    condition = trial_sequence[trial_num]
    word = word_sequence[trial_num]
    isi = isis[trial_num]

    # Select trigger color
    if condition == 'standard':
        trig_color = rgb_255_to_psychopy(TRIGGER_STANDARD)
        el_msg = 'standard'   # FIXED: matches CSV Condition label
    else:
        trig_color = rgb_255_to_psychopy(TRIGGER_DEVIANT)
        el_msg = 'deviant'    # FIXED: matches CSV Condition label

    # --- STIMULUS ONSET: draw word + trigger on same frame ---
    word_stim.text = word
    word_stim.draw()
    trigger_patch.fillColor = trig_color
    trigger_patch.draw()

    # Mark trial in EDF
    if EYELINK_AVAILABLE and el_tracker is not None:
        el_tracker.sendMessage('TRIALID %d' % (trial_num + 1))

        # Update Host PC status bar
        el_tracker.sendCommand(
            "record_status_message 'TRIAL %d/%d  %s  %s'" %
            (trial_num + 1, N_TOTAL, condition, word)
        )

    # Send EyeLink message at the flip
    if EYELINK_AVAILABLE and el_tracker is not None:
        win.callOnFlip(el_tracker.sendMessage, el_msg)
    onset_time = win.flip()

    # Let word display for its duration
    core.wait(WORD_DURATION)

    # --- TRIGGER RESET: return pixel to black during ISI ---
    fixation.draw()
    trigger_patch.fillColor = rgb_255_to_psychopy(TRIGGER_RESET)
    trigger_patch.draw()
    win.flip()

    # Log trial
    trial_log.append({
        'TRIALID': trial_num + 1,
        'Condition': condition,
        'Word': word,
        'onset_time': f"{onset_time:.6f}",
        'ISI': f"{isi:.4f}"
    })

    # Wait for ISI (offset to next onset)
    core.wait(isi)

    # --- BLINK TRIAL: green fixation after each deviant ---
    if condition == 'deviant':
        # Show green fixation cross with blink trigger
        fixation_blink.draw()
        trigger_patch.fillColor = rgb_255_to_psychopy(TRIGGER_BLINK)
        trigger_patch.draw()

        if EYELINK_AVAILABLE and el_tracker is not None:
            el_tracker.sendMessage('blink')   # FIXED: matches CSV Condition label
            el_tracker.sendCommand(
                "record_status_message 'TRIAL %d/%d  BLINK'" %
                (trial_num + 1, N_TOTAL)
            )
        blink_onset_time = win.flip()

        core.wait(BLINK_DURATION)

        # Return to fixation, reset trigger
        fixation.draw()
        trigger_patch.fillColor = rgb_255_to_psychopy(TRIGGER_RESET)
        trigger_patch.draw()
        win.flip()

        # Log blink trial
        trial_log.append({
            'TRIALID': trial_num + 1,
            'Condition': 'blink',
            'Word': '',
            'onset_time': f"{blink_onset_time:.6f}",
            'ISI': ''
        })

# =============================================================================
# STOP RECORDING
# =============================================================================

if EYELINK_AVAILABLE and el_tracker is not None:
    el_tracker.sendMessage('EXPERIMENT_END')

    # Add 100 ms to catch final events
    pylink.pumpDelay(100)
    el_tracker.stopRecording()

# =============================================================================
# SAVE LOG FILE
# =============================================================================

csv_filename = filename + '.csv'
with open(csv_filename, 'w', newline='') as f:
    writer = csv.DictWriter(
        f, fieldnames=['TRIALID', 'Condition', 'Word', 'onset_time', 'ISI']
    )
    writer.writeheader()
    writer.writerows(trial_log)

print(f"Log saved to: {csv_filename}")

# =============================================================================
# END - DOWNLOAD EDF AND CLOSE
# =============================================================================

end_msg = visual.TextStim(
    win,
    text="The experiment is complete.\n\nThank you!\n\nPress SPACE to exit.",
    color='white',
    height=30,
    wrapWidth=800
)
end_msg.draw()
win.flip()
event.waitKeys(keyList=['space'])

if EYELINK_AVAILABLE and el_tracker is not None:
    terminate_task(win, el_tracker, edf_file, session_folder,
                   local_edf_name)
else:
    win.close()
    core.quit()
    sys.exit()
