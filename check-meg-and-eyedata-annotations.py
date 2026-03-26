import mne


print ("Eye recording annotations:")
print ("")
eye = mne.io.read_raw_eyelink("/Users/markpinsk/opm-projects/oddball/data/oddball/raw/sub_001/eyetracking/recording.asc", verbose=False)
print({a for a in set(eye.annotations.description) if not a.startswith('TRIALID')})

print ("")
print ("MEG recording annotations (after running BIDS pipeline):")
print ("")
raw = mne.io.read_raw_fif('/Users/markpinsk/opm-projects/oddball/data/oddball/bids/derivatives/analysis1__test-online/sub-001/ses-01/meg/sub-001_ses-01_task-oddball_run-01_proc-filt_raw.fif', preload=False, verbose=False)
print({a for a in set(raw.annotations.description) if not a.startswith('HFC')})